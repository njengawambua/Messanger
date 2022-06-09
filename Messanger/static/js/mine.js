'use strict'

function hasMedia() {
    navigator.mediaDevices
        .getUserMedia({
            audio: false,
            video: true
        })
        .then(gotStream)
        .catch(function(e) {
            alert('getUserMedia() error: ' + e.name)
        })
}

function gotStream(stream) {
    console.log('Adding local stream.')
    localVideo = document.getElementById('myVideo')
    localVideo.src = window.URL.createObjectURL(stream)


}

hasMedia()

navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;

var con = {
    audio: true,
    video: true
};
var localVideo = document.getElementById('myVideo');

function succfall(stream) {
    window.stream = stream;

    if (window.URL) {
        localVideo.src = window.URL.createObjectURL(stream)

    } else {
        localVideo.src = stream;
    }
    localVideo.play();

}

function errcallback(error) {
    console.log("navigator error", error)
}

navigator.getUserMedia(con, succfall, errcallback)