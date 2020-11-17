async function postData(name = '', url = '', data) {
    let fd = new FormData;
    fd.append(name, data);
    fd.append("csrfmiddlewaretoken", CSRF_TOKEN);

    const response = await fetch(url, {method: "POST", body: fd, credentials: 'same-origin',});

    if (response.status === 200) {
        return await response.json();
    } else if (response.status === 400) {
        alert((await response.json()).error);
        throw response.status;
    }
}

function upload_audio(data) {
    postData("audio_upload", '', data).then((data) => {
        sessionStorage.setItem("wrapper2", data.html);
        window.location = window.location.href;
    });
}
