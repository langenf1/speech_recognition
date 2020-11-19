let counting, counter, elem, timer, i, limit, rec, should_record, mediaRecorder, error, full_text, oldContent;
let recordedChunks = [];

window.onload = function () {
    // Initialize variables
    limit = 60; // Limit in seconds
    error = 0; // Timer error
    i = 0;
    counting = false;
    fig = document.getElementById("record_figure");
    counter = document.getElementById("counter");
    elem = document.getElementById("recorder");
    full_text = document.getElementById("full_text");
    full_text.innerHTML = "Transcribed Audio: ";
    counter.innerHTML = "<h4>" + 0 + "</h4>";
    should_record = false;
};

function onLoad() {
    // This code is always executed on page load
    document.getElementById("recorder").onclick = function () {
        if (elem.value === "notrec") {
            full_text.innerHTML = "Transcribed Audio: ";
            // Store old button content in case we need to reset the button
            oldContent = fig.innerHTML;

            elem.value = "rec";
            fig.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">' +
                '<path d="M19 2c1.654 0 3 1.346 3 3v14c0 1.654-1.346 3-3 3h-14c-1.654 0-3-1.346-3-3v-14c0-1.654 ' +
                '1.346-3 3-3h14zm0-2h-14c-2.762 0-5 2.239-5 5v14c0 2.761 2.238 5 5 5h14c2.762 0 5-2.239 ' +
                '5-5v-14c0-2.761-2.238-5-5-5z"></path></svg>';
            should_record = true;

            // Get (access to) the microphone stream
            navigator.mediaDevices.getUserMedia({audio: true, video: false})
                .then(handleSuccess)
                .then(start)
                .catch((err) => {
                    console.error(err);
                    alert("We need your permission for access to your microphone so we can record an audio sample");
                    elem.value = "notrec";
                    fig.innerHTML = oldContent;
                });
        } else {
            elem.value = "notrec";
            fig.innerHTML = oldContent;
            mediaRecorder.stop();
            reset();
            should_record = false;
        }
    };

    if (elem.value === "notrec") {
        counting = false;
    } else {
        counting = true;
        increase(counter);
    }
}

function start() {
    if (!timer) {
        timer = setInterval("increase()", 10);
    }
}

function increase() {
    i++;
    if (i < limit * 100 && i % ((limit * 100)/15) === 0) {
        mediaRecorder.stop();
        mediaRecorder.start();
    } else {
        if (i >= limit * 100) {
            reset();
            elem.value = "notrec";
            fig.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">\n' +
                '<path d="M12 2c1.103 0 2 .897 2 2v7c0 1.103-.897 2-2 2s-2-.897-2-2v-7c0-1.103.897-2\n' +
                '2-2zm0-2c-2.209 0-4 1.791-4 4v7c0 2.209 1.791 4 4 4s4-1.791 4-4v-7c0-2.209-1.791-4-4-4zm8\n' +
                ' 9v2c0 4.418-3.582 8-8 8s-8-3.582-8-8v-2h2v2c0 3.309 2.691 6 6 6s6-2.691 6-6v-2h2zm-7\n' +
                ' 13v-2h-2v2h-4v2h10v-2h-4z"></path></svg>';
            should_record = false;
            mediaRecorder.stop();
        }
    }
    counter.innerHTML = "<h4>" + i / 100 + "</h4>";
}

function stop() {
    clearInterval(timer);
    timer = null;
}

function reset() {
    stop();
    i = 0;
    counting = false;
    counter.innerHTML = "<h4>" + i + "</h4>";
}

const handleSuccess = function (stream) {
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(1024, 1, 1);

    source.connect(processor);
    processor.connect(context.destination);

    const options = {mimeType: 'audio/webm'};
    mediaRecorder = new MediaRecorder(stream, options);
    if (should_record === true) {
        console.log("Started Recording");
        mediaRecorder.start();
    }

    mediaRecorder.addEventListener('dataavailable', function (e) {
        if (e.data.size > 0) {
            recordedChunks.push(e.data);
        }
    });

    mediaRecorder.addEventListener('stop', function () {
        console.log("Stopped Recording");
        postData("audio_recording", '', recordedChunks).then((data) => {
            full_text.innerHTML = full_text.innerHTML + " " + data['text'];
        });
    })
};

async function postData(name = '', url = '', data) {
    let fd = new FormData;

    if (name === "audio_recording") {
        fd.append(name, new Blob(data));
        recordedChunks = [];
    } else {
        fd.append(name, data);
    }
    fd.append("csrfmiddlewaretoken", CSRF_TOKEN);

    const response = await fetch(url, {method: "POST", body: fd, credentials: 'same-origin',});

    if (response.status === 200) {
        return await response.json()
    } else if (response.status === 400) {
        alert((await response.json()).error);
        throw response.status;
    }
}

function upload_audio(data) {
    postData("audio_upload", '', data).then((data) => {
        full_text.innerHTML = "Transcribed Audio: " + data['text'];
    });
}
