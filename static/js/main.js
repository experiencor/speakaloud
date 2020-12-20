function levenshteinSimilarity(s1, s2) {
    var longer = s1;
    var shorter = s2;
    if (s1.length < s2.length) {
        longer = s2;
        shorter = s1;
    }
    var longerLength = longer.length;
    if (longerLength == 0) {
        return 1.0;
    }
    return (longerLength - levenshteinDistance(longer, shorter)) / parseFloat(longerLength);
}


function levenshteinDistance(a, b) {
    if (a === b) {
        return 0;
    }

    if (a.length > b.length) {
        var tmp = a;
        a = b;
        b = tmp;
    }

    var la = a.length;
    var lb = b.length;

    while (la > 0 && (a.charCodeAt(la - 1) === b.charCodeAt(lb - 1))) {
        la--;
        lb--;
    }

    var offset = 0;

    while (offset < la && (a.charCodeAt(offset) === b.charCodeAt(offset))) {
        offset++;
    }

    la -= offset;
    lb -= offset;

    if (la === 0 || lb < 3) {
        return lb;
    }

    var x = 0;
    var y;
    var d0;
    var d1;
    var d2;
    var d3;
    var dd;
    var dy;
    var ay;
    var bx0;
    var bx1;
    var bx2;
    var bx3;

    var vector = [];

    for (y = 0; y < la; y++) {
        vector.push(y + 1);
        vector.push(a.charCodeAt(offset + y));
    }

    var len = vector.length - 1;

    for (; x < lb - 3;) {
        bx0 = b.charCodeAt(offset + (d0 = x));
        bx1 = b.charCodeAt(offset + (d1 = x + 1));
        bx2 = b.charCodeAt(offset + (d2 = x + 2));
        bx3 = b.charCodeAt(offset + (d3 = x + 3));
        dd = (x += 4);
        for (y = 0; y < len; y += 2) {
            dy = vector[y];
            ay = vector[y + 1];
            d0 = _min(dy, d0, d1, bx0, ay);
            d1 = _min(d0, d1, d2, bx1, ay);
            d2 = _min(d1, d2, d3, bx2, ay);
            dd = _min(d2, d3, dd, bx3, ay);
            vector[y] = dd;
            d3 = d2;
            d2 = d1;
            d1 = d0;
            d0 = dy;
        }
    }

    for (; x < lb;) {
        bx0 = b.charCodeAt(offset + (d0 = x));
        dd = ++x;
        for (y = 0; y < len; y += 2) {
            dy = vector[y];
            vector[y] = dd = _min(dy, d0, dd, bx0, vector[y + 1]);
            d0 = dy;
        }
    }

    return dd;
};


function _min(d0, d1, d2, bx, ay) {
    return d0 < d1 || d2 < d1
            ? d0 > d2
                    ? d2 + 1
                    : d0 + 1
            : bx === ay
                    ? d1
                    : d1 + 1;
}


class StopWatch {
    constructor() {
        this.timeElapsed = 0;
        this.startTime = null;
        this.lastTime = 0
    }

    start() {
        if (!this.startTime) {
            this.startTime = new Date();
        }
    }

    stop() {
        if (!!this.startTime) {
            this.timeElapsed += (new Date() - this.startTime);
            this.startTime = null;
        }
    }

    getTime() {
        if (!this.startTime) {
            return this.timeElapsed
        } else {
            return this.timeElapsed + (new Date() - this.startTime);
        }
    }

    getDuration(reset = true) {
        var currTime = this.getTime()
        var duration = currTime - this.lastTime
        if (reset) {
            this.lastTime = currTime
        }
        return [duration, currTime]
    }
}

function setCookie(name, value, days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function eraseCookie(name) {   
    document.cookie = name+'=; Max-Age=-99999999;';  
}

function getUser(user_name) {
    return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "create_user/" + user_name, true);
        xhr.setRequestHeader("Content-Type", "application/json");

        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                var jsonContent = JSON.parse(xhr.responseText);            
                resolve(jsonContent["user_id"])
            }
        }
        xhr.send();
    });
}

function getUserProfile(user_id) {
    return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "get_user_profile/" + user_id, true);
        xhr.setRequestHeader("Content-Type", "application/json");

        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                var jsonContent = JSON.parse(xhr.responseText);
                resolve(jsonContent)
            }
        }
        xhr.send();   
    }) 
}