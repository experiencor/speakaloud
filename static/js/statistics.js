var user_id = getCookie("user_id")
getStats()

function getStats() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "get_stats/" + String(user_id), true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var jsonContent = JSON.parse(xhr.responseText);
            draw_hard_word(jsonContent["word_stats"])
            draw_word_time(jsonContent["daily_stats"])
            draw_word_count(jsonContent["daily_stats"])
        }
    }
    xhr.send();
}

function draw_hard_word(word_list) {
    trials = []
    durations = []
    for (var i = 0; i < word_list.length; ++i) {
        row = word_list[i]
        trials.push(row[0]);
        durations.push({y: row[1]/1000, color: "#4285f4"})
    }

    while (trials.length < 10) {
        trials.push(" ")
        durations.push({})
    }

    Highcharts.chart('hard_word', {
        chart: {
            type: 'bar',
            height: 528
        },
        title: {
            text: ''
        },
        subtitle: {
            text: ''
        },
        xAxis: {
            categories: trials,
            title: {
                text: null
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Thời Gian',
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            }
        },
        tooltip: {
            valueSuffix: 's'
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'top',
            x: -40,
            y: 80,
            floating: true,
            borderWidth: 1,
            backgroundColor:
                Highcharts.defaultOptions.legend.backgroundColor || '#FFFFFF',
            shadow: true
        },
        credits: {
            enabled: false
        },
        series: [{
            data: durations
        }],
        legend: false
    });
}

function draw_word_time(word_list) {
    trials = []
    counts = []
    for (var i = 0; i < word_list.length; ++i) {
        row = word_list[i]
        trials.push(row[0]);
        counts.push({y: row[1]/1000, color: "#4285f4"})
    }

    while (trials.length < 10) {
        trials.push(" ")
        counts.push({})
    }

    Highcharts.chart('word_time', {
        chart: {
            type: 'column',
            height: 200,
        },
        title: {
            text: ''
        },
        subtitle: {
            text: ''
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Seconds'
            }
        },
        xAxis: {
            categories: trials
        },  
        series: [{
            data: counts

        }],
        legend: false
    });
}

function draw_word_count(word_list) {
    trials = []
    counts = []
    for (var i = 0; i < word_list.length; ++i) {
        row = word_list[i]
        trials.push(row[0]);
        counts.push({y: row[2], color: "#4285f4"})
    }

    while (trials.length < 10) {
        trials.push(" ")
        counts.push({})
    }

    Highcharts.chart('word_count', {
        chart: {
            type: 'column',
            height: 200,
        },
        title: {
            text: ''
        },
        subtitle: {
            text: ''
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Lượng Từ'
            }
        },
        xAxis: {
            categories: trials
        },  
        series: [{
            data: counts

        }],
        legend: false
    });
}

async function login() {
    user_name = "";
    person = prompt("Please enter your name:", "");
    if ((person !== null) & (person !== "")) {
        user_name = person;
        setCookie("user_name", user_name, 14)

        user_id = await getUser(user_name)
        setCookie("user_id", user_id, 14)
        getStats()
    }
}