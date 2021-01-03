var EXACT_MATCH = 5000
var STEM_MATCH = 10000
var PARTIAL_MATCH = 15000

var user_name = getCookie("user_name");
var user_id = null;
var paragraph_id = null;
var session_id = null;
var next_count = null;
var skipwords = null;
var paragraph = [];
var wordMapping = null;
var ipa = [];
var current_ipa = "";
var curr_paragraph_indx = 0;
var curr_interim_indx = 0;
var curr_interim = ""
var suggestionList = null
var manual_reset = false

var stopWatch = new StopWatch();
var started = null;
var final_sent_started_at = 0
var transcript = "";
var is_building_final_sent = false

// entry point to client-side logic
if (!('webkitSpeechRecognition' in window)) {
    upgrade();
} else {
    var recognition = new window.webkitSpeechRecognition;
    var recognizing = false;
    recognition.lang = "en-US"
    recognition.continuous = true;
    recognition.interimResults = true;

    $(document).ready(function() {
        $('#paragraph').textcomplete([
            {
                // #3 - Rgular experession used to trigger search
                match: "",

                // #4 - Function called at every new keystroke
                search: function(query, callback) {
                    callback([{name: current_ipa}, {name: curr_interim}])
                },

                // #5 - Template used to display each result obtained by the Algolia API
                template: function (hit) {
                    return hit.name;
                },
            }
        ]);
    });    

    $(document).ready(function(){
        $("#paragraph").on("keypress", function(e) {
            e.preventDefault();
        });
    });

    startItAll()
}

async function startItAll() {
    while (user_name === null | user_name === "") {
        user_name = prompt("Please enter your name:", "");
    }
    setCookie("user_name", user_name, 14)

    user_id = await getUser(user_name);
    setCookie("user_id", user_id);

    results = await getUserProfile(user_id);
    next_count = results["next_count"];
    paragraph_id = results["paragraph_id"];
    wordMapping = results["word_mapping"].reduce(function(map, obj) { map[obj[0]] = obj[1]; return map }, {})
    paragraph = results["words"];
    norm_para = paragraph.map(word => normalize(word))
    ipa = results["ipas"];
    stems = results["stems"];
    difficult_words = results["difficult_words"]
    highlight_paragraph = paragraph.map((word, index) => {
        if (difficult_words[index] == 1) {
            return '<span class="read_para">' + word + '</span>'
        } else {
            return word
        }
    })
    skipwords = new Set(results["skipwords"]);
    min_completion_time = results["min_completion_time"];
    word_count = results["word_count"];
    average_duration = roundTwo(results["average_duration"]/word_count/1000);

    reset();

    recognition.onstart = function () {
        recognizing = true;
    };

    recognition.onend = function () {
        recognizing = false;
    };

    recognition.onerror = function (event) {
        recognizing = false;
    };

    recognition.onend = function() {
        recognition.start()
    }

    recognition.onresult = function(event) {
        if (!is_building_final_sent) {
            if (!document.hasFocus()) {
                return
            }
            is_building_final_sent = true
            final_sent_started_at = stopWatch.getTime()
            stopWatch.start();
        }

        transcript = ""
        isFinal = false
        for (var i = event.resultIndex; i < event.results.length; ++i) {
            isFinal |= event.results[i].isFinal;
            transcript += event.results[i][0].transcript;
        }
        
        words = transcript.trim().split(" ")
        i = curr_interim_indx
        while (i < words.length) {
            if ((curr_paragraph_indx < paragraph.length) && 
                letItPass(normalize(words[i]), 
                          norm_para[curr_paragraph_indx], 
                          stems[curr_paragraph_indx], 
                          stopWatch.getDuration(false)[0])) {
                [duration, completed_at] = stopWatch.getDuration();

                logEvent(user_id, 
                         paragraph_id, 
                         session_id, 
                         curr_paragraph_indx, 
                         paragraph[curr_paragraph_indx], 
                         paragraph.length, 
                         duration, 
                         completed_at);

                curr_paragraph_indx += 1
                findNextWord();
                curr_interim_indx = i + 1

                $('#paragraph').html('<span class="read_para">' + highlight_paragraph.slice(0, curr_paragraph_indx).join(" ") + "</span> " +
                    '<span id="unread">' + highlight_paragraph.slice(curr_paragraph_indx).join(" ")) + "</span> "
                
                setIPA();
                triggerContextMenu();
            }
            i += 1
        }

        curr_interim = words.slice(curr_interim_indx).join(" ")
        if (suggestionList === null) {
            suggestionList = document.getElementById("textcomplete-dropdown-1")
        }
        if (suggestionList.style.display == "none") {
            triggerContextMenu()
        } else {
            interim = suggestionList.children[1]
            interim.innerHTML = "<a>" + curr_interim + "</a>"
        }

        if (curr_paragraph_indx == paragraph.length) {
            recognition.stop()
        }

        if (isFinal) {
            curr_interim_indx = 0
            curr_interim = ""
            triggerContextMenu()

            completed_at = stopWatch.getTime()
            var word = "";
            if (curr_paragraph_indx == paragraph.length) {
                const ut = new SpeechSynthesisUtterance('Well done!');
                speechSynthesis.speak(ut);
                logFinalSent(user_id, 
                             paragraph_id, 
                             session_id, 
                             transcript, 
                             curr_paragraph_indx, 
                             word, 
                             final_sent_started_at, 
                             completed_at, 
                             drawReadingHistory)
                reset();
            } else {
                is_building_final_sent = false
                word = paragraph[curr_paragraph_indx]
                stopWatch.stop()
                logFinalSent(user_id, 
                             paragraph_id, 
                             session_id, 
                             transcript, 
                             curr_paragraph_indx, 
                             word, 
                             final_sent_started_at, 
                             completed_at)
                if (manual_reset) {
                    manual_reset = false;
                    reset();
                }
            }
            
        }
    }

    if (!recognizing) {
        recognition.start()
    }    

    drawReadingHistory();
    document.getElementById("word_count").innerHTML = word_count
    document.getElementById("average_duration").innerHTML = average_duration
}

function letItPass(spoken_word, norm_word, stem_word, duration) {
    if (duration <= EXACT_MATCH) {
        return spoken_word === norm_word
    } else if (duration <= STEM_MATCH) {
        return (spoken_word.slice(0, stem_word.length) == stem_word)
    } else {
        duration = Math.min(duration, PARTIAL_MATCH)
        threshold = (2 * PARTIAL_MATCH - STEM_MATCH - duration) / 2 / (PARTIAL_MATCH - STEM_MATCH)
        similarity = levenshteinSimilarity(spoken_word, norm_word)
        return similarity >= threshold
    }
}

function findNextWord() {
    while (curr_paragraph_indx < norm_para.length) {
        word = norm_para[curr_paragraph_indx]
        pronunciation = ipa[curr_paragraph_indx]
        if ((pronunciation.length == 0) | (word === "") | skipwords.has(word) | word.includes("@")) {
            curr_paragraph_indx += 1
        } else {
            break
        }
    }
}

function resetRecognition() {
    recognition.stop()

    if (is_building_final_sent) {
        is_building_final_sent = false

        if (curr_paragraph_indx == paragraph.length) {
            word = paragraph[curr_paragraph_indx]
        } else {
            word = ""
        }

        completed_at = stopWatch.getTime()
        stopWatch.stop()
        logFinalSent(user_id, 
                     paragraph_id, 
                     session_id, 
                     transcript, 
                     curr_paragraph_indx, 
                     word, 
                     final_sent_started_at, 
                     completed_at)

        curr_interim_indx = 0
        curr_interim = ""
        triggerContextMenu()
    }
}

function logEvent(user_id, paragraph_id, session_id, word_index, word, paragraph_length, duration, completed_at) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "event/", true);
    xhr.setRequestHeader("Content-Type", "application/json");

    var data = JSON.stringify({"user_id": user_id, 
                               "paragraph_id": paragraph_id, 
                               "session_id": session_id, 
                               "word_index": word_index, 
                               "word": normalize(word),
                               "paragraph_length": paragraph_length,
                               "duration": duration, 
                               "completed_at": completed_at})
    xhr.send(data);
}

function logFinalSent(user_id, paragraph_id, session_id, sentence, word_index, word, started_at, completed_at, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "final_sent/", true);
    xhr.setRequestHeader("Content-Type", "application/json");

    var data = JSON.stringify({"user_id": user_id, 
                               "session_id": session_id, 
                               "paragraph_id": paragraph_id, 
                               "sentence": sentence, 
                               "word_index": word_index, 
                               "word": normalize(word),
                               "started_at": started_at,
                               "completed_at": completed_at})
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            if (callback) {
               callback()
            }
        }
    }
    xhr.send(data);
}

function normalize(word) {
    word = word.toLowerCase()
    word = word.replace(/^[^a-zA-Z0-9]*|/mg, "")
    word = word.replace(/[^a-zA-Z0-9]*$|/mg, "")
    if (word in wordMapping) {
        return wordMapping[word]
    }
    return word
}

function readit() {
    if (curr_paragraph_indx < paragraph.length) {
        text = paragraph.slice(curr_paragraph_indx, curr_paragraph_indx+3).join(" ")
        var msg = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(msg);
    }
}

function clockRunning(){
    var timeElapsed = new Date(stopWatch.getTime())
    var hour = timeElapsed.getUTCHours()
    , min = timeElapsed.getUTCMinutes()
    , sec = timeElapsed.getUTCSeconds()
    , ms = timeElapsed.getUTCMilliseconds();

    document.getElementById("minutes").innerHTML = min > 9 ? min : "0" + min
    document.getElementById("seconds").innerHTML = sec > 9 ? sec : "0" + sec
    document.getElementById("milliseconds").innerHTML = ms > 99 ? ms : ms > 9 ? "0" + ms : "00" + ms
};

function setIPA() {
    if (curr_paragraph_indx < ipa.length) {
        var choices = ipa[curr_paragraph_indx];
        if (choices.length === 0) {
            current_ipa = "/" + paragraph[curr_paragraph_indx] + "/"
        } else {
            current_ipa = "/" + choices[0] + "/"
            for (i = 1; i < choices.length; i++) {
                current_ipa += ", " + "/" + choices[i] + "/"
            }
        }
    }
}

function reset(){
    is_building_final_sent = false
    curr_paragraph_indx = 0;
    findNextWord();
    setIPA();
    session_id = generateRandomString(16);

    document.getElementById('paragraph').innerHTML = "\u200B" + '<span id="unread">' + highlight_paragraph.join(" ") + "</span>"
    document.getElementById('change_para').innerHTML = "Đổi Đoạn: " + next_count
    if (next_count == 0){
        document.getElementById("change_para").disabled = true;
    } else {
        document.getElementById("change_para").disabled = false;
    }
    curr_interim = ""
    setTimeout(triggerContextMenu, 10);  
    setTimeout(triggerContextMenu, 10);

    stopWatch = new StopWatch();
    started = setInterval(clockRunning, 200);  
}

function triggerContextMenu() {
    var el = $('#unread')[0];
    var range = document.createRange();
    var sel = window.getSelection();
    if (el.childNodes[0]) {
        range.setStart(el.childNodes[0], 0);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        $('#paragraph').data('textComplete').trigger("");/**/
    }
}

function generateRandomString(length) {
    var result = Date.now().toString(36)
    for ( var i = 0; i < 8; i++ ) {
        result += Math.floor(Math.random() * 36).toString(36)
    }
    return result;
}

function drawReadingHistory() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "get_history/" + String(user_id) + "/" + String(paragraph_id), true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var jsonContent = JSON.parse(xhr.responseText);

            if (jsonContent.length == 0) {
                document.getElementById('history').innerHTML = ""
                return
            }
            
            rows = [['Time', 'Duration', { role: 'style' }, 'Record Time']]
            trials = []
            durations = []
            records = []
            for (var i = 0; i < jsonContent.length; ++i) {
                row = jsonContent[i]

                trials.push(i + 1);
                durations.push({y: roundTwo(row["duration"]/1000), color: row["no_repetition"] ? "red" : "#4285f4"})
                records.push(roundTwo(min_completion_time/1000));
            }

            while (trials.length < 10) {
                trials.push(" ")
                durations.push({})
                records.push({})
            }

            Highcharts.chart('history', {
                chart: {
                    zoomType: 'xy'
                },
                title: {
                    text: ''
                },
                subtitle: {
                    text: ''
                },
                xAxis: {
                    categories: trials
                },
                yAxis: [{ // Primary yAxis
                    labels: {
                        format: '{value}s',
                        style: {
                            color: Highcharts.getOptions().colors[1]
                        }
                    },
                    title: {
                        text: 'Thời Gian',
                        style: {
                            color: Highcharts.getOptions().colors[1]
                        }
                    }
                }],
                tooltip: {
                    shared: true
                },
                plotOptions: {
                    column: {
                        dataLabels: {
                            enabled: true
                        }
                    }
                },
                legend: false,
                series: [{
                    name: 'Thời Gian',
                    type: 'column',
                    data: durations,
                    tooltip: {
                        valueSuffix: 's'
                    }
                },{
                    name: 'Thời Gian',
                    type: 'spline',
                    data: records,
                    tooltip: {
                        valueSuffix: 's'
                    }
                }]
            });
        }
    }
    xhr.send();
}

function login() {
    user_name = "";
    person = prompt("Please enter your name:", "");
    if ((person !== null) & (person !== "")) {
        user_name = person;
        setCookie("user_name", user_name, 14)
        startItAll()
    }
}

document.addEventListener("keydown", function(e) {
    if (e.keyCode == 32) {
        e.preventDefault();
        readit();
    }

    if (e.keyCode == 13) {
        e.preventDefault();
        if (is_building_final_sent) {
            recognition.stop();
            manual_reset = true;
        } else {
            reset();
        }
    }

    if (e.keyCode == 17) {
        e.preventDefault();
    }
    triggerContextMenu()
});

document.addEventListener("keyup", function(e) {
    if (e.keyCode == 32) {
        e.preventDefault();
    }

    if (e.keyCode == 13) {
        e.preventDefault();
    }

    if (e.keyCode == 17) {
        e.preventDefault();
    }
    triggerContextMenu()
});

function nextPara() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "next_para/" + String(user_id), true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var jsonContent = JSON.parse(xhr.responseText);
            next_count = jsonContent["next_count"];
            startItAll();
        }
    }
    xhr.send();    
}