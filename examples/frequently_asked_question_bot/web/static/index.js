var element = $('.floating-chat');
var client_id = createUUID();

/*
Here Websocket URI is computed using current location. (https://stackoverflow.com/a/10418013)
I don't know how reliable that is, in prod it is probably
better to use hardcoded uri, e.g. ws_uri = "ws://example.com/ws/..."
*/
var loc = window.location, ws_uri;
if (loc.protocol === "https:") {
    ws_uri = "wss:";
} else {
    ws_uri = "ws:";
}
ws_uri += "//" + loc.host;
ws_uri += loc.pathname + "ws/" + client_id;

var ws = new WebSocket(ws_uri);
ws.onmessage = receiveBotMessage;

setTimeout(function() {
    element.addClass('enter');
}, 1000);

element.click(openElement);

function openElement() {
    var messages = element.find('.messages');
    var textInput = element.find('.text-box');
    element.find('>i').hide();
    element.addClass('expand');
    element.find('.chat').addClass('enter');
    var strLength = textInput.val().length * 2;
    textInput.keydown(onMetaAndEnter).prop("disabled", false).focus();
    element.off('click', openElement);
    element.find('.header button').click(closeElement);
    element.find('#sendMessage').click(sendNewMessage);
    messages.scrollTop(messages.prop("scrollHeight"));
}

function closeElement() {
    element.find('.chat').removeClass('enter').hide();
    element.find('>i').show();
    element.removeClass('expand');
    element.find('.header button').off('click', closeElement);
    element.find('#sendMessage').off('click', sendNewMessage);
    element.find('.text-box').off('keydown', onMetaAndEnter).prop("disabled", true).blur();
    setTimeout(function() {
        element.find('.chat').removeClass('enter').show()
        element.click(openElement);
    }, 500);
}

function createUUID() {
    // http://www.ietf.org/rfc/rfc4122.txt
    var s = [];
    var hexDigits = "0123456789abcdef";
    for (var i = 0; i < 36; i++) {
        s[i] = hexDigits.substr(Math.floor(Math.random() * 0x10), 1);
    }
    s[14] = "4"; // bits 12-15 of the time_hi_and_version field to 0010
    s[19] = hexDigits.substr((s[19] & 0x3) | 0x8, 1); // bits 6-7 of the clock_seq_hi_and_reserved to 01
    s[8] = s[13] = s[18] = s[23] = "-";

    var uuid = s.join("");
    return uuid;
}

function addMessageToContainer(messageToAdd, type) {
    var newMessage = messageToAdd;

    if (!newMessage) return;

    var messagesContainer = $('.messages');

    messagesContainer.append([
        `<li class="${type}">`,
        newMessage,
        '</li>'
    ].join(''));

    messagesContainer.animate({
        scrollTop: messagesContainer.prop("scrollHeight")
    }, 250);

    return newMessage;
}

function sendNewMessage() {
    var input = document.getElementById("messageText");
    var result = addMessageToContainer(input.value, "user");
    ws.send(result);
    input.value = '';
    event.preventDefault();
}

function receiveBotMessage(event) {
    addMessageToContainer(event.data, "bot");
}

function onMetaAndEnter(event) {
    if (event.keyCode == 13) {
        sendNewMessage();
    }
}