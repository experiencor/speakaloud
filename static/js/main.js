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