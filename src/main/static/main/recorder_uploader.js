let counting, counter, elem, timer, i, limit, rec, should_record, mediaRecorder, error, full_text, oldContent, seconds_per_cut;
let wer, wcr, rtf, precision_micro, precision_macro, recall_micro, recall_macro, f1_micro, f1_macro, reset_text, input_text;
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
    input_text = document.getElementById("text_area")
    wer = document.getElementById("wer");
    wcr = document.getElementById("wcr");
    rtf = document.getElementById("rtf");
    precision_micro = document.getElementById("precision_micro");
    precision_macro = document.getElementById("precision_macro");
    recall_micro = document.getElementById("recall_micro");
    recall_macro = document.getElementById("recall_macro");
    f1_micro = document.getElementById("f1_micro");
    f1_macro = document.getElementById("f1_macro");
    full_text.innerHTML = "";
    input_text.value = "";

    wer.innerHTML = "0.00";
    wcr.innerHTML = "0.00";
    rtf.innerHTML = "0.00";
    precision_micro.innerHTML = "0.00";
    precision_macro.innerHTML = "0.00";
    recall_micro.innerHTML = "0.00";
    recall_macro.innerHTML = "0.00";
    f1_micro.innerHTML = "0.00";
    f1_macro.innerHTML = "0.00";

    counter.innerHTML = "<h4>" + 0 + "</h4>";
    seconds_per_cut = document.getElementById("num");
    should_record = false;
    reset_text = false;
};

function onLoad() {
    // This code is always executed on page load
    document.getElementById("recorder").onclick = function () {
        if (elem.value === "notrec") {
            full_text.innerHTML = "";
            wer.innerHTML = 0.0
            wcr.innerHTML = 0.0
            rtf.innerHTML = 0.0

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
            should_record = false;
            if ((i / (seconds_per_cut.value * 100)) <= 1) {
                reset_text = true;
            } else {
                reset_text = false;
            }
            mediaRecorder.stop();
            reset();
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
    if (i < limit * 100 && i > 0) {
        if (i % (seconds_per_cut.value * 100) === 0) {
            if ((i / (seconds_per_cut.value * 100)) < 2) {
                reset_text = true;
            } else {
                reset_text = false;
            }
            mediaRecorder.stop();
            mediaRecorder.start();
        }
    } else {
        if (i >= limit * 100) {
            reset();
            elem.value = "notrec";
            fig.innerHTML = oldContent;
            should_record = false;
            reset_text = false;
            mediaRecorder.stop();
        }
    }
    i++;
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
    mediaRecorder.stop_reset = function() {};

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
        console.log("Stopped recording");
        console.log("Resetting text: " + reset_text.toString())
        postData("audio_recording", '', recordedChunks, reset_text).then((data) => {
            full_text.innerHTML = data['text'];
            upload_text(input_text.value);
        });
    })
};

async function postData(name = '', url = '', data, reset = true) {
    let fd = new FormData;

    if (name === "audio_recording") {
        fd.append(name, new Blob(data));
        recordedChunks = [];
    } else {
        fd.append(name, data);
    }
    fd.append("reset", reset.toString());

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
    postData("audio_upload", '', data, true).then((data) => {
        full_text.innerHTML = data['text'];
        upload_text(input_text.value);
    });
}

function upload_text(data) {
    postData("text_upload", '', data).then((data) => {
        wer.innerHTML = data['wer'];
        wcr.innerHTML = data['wcr'];
        rtf.innerHTML = data['rtf'];
        precision_micro.innerHTML = data['precision_micro'];
        precision_macro.innerHTML = data['precision_macro'];
        recall_micro.innerHTML = data['recall_micro'];
        recall_macro.innerHTML = data['recall_macro'];
        f1_micro.innerHTML = data['f1_micro'];
        f1_macro.innerHTML = data['f1_macro'];
    });
}
