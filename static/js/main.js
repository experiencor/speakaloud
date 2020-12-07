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

    getDuration() {
        var currTime = this.getTime()
        var duration = currTime - this.lastTime
        this.lastTime = currTime
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