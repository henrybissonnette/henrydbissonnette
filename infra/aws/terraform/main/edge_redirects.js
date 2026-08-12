function appendQueryString(location, querystring) {
    var parts = [];

    for (var name in querystring) {
        if (!Object.prototype.hasOwnProperty.call(querystring, name)) {
            continue;
        }

        var entry = querystring[name];
        var values = entry.multiValue || [entry];
        for (var index = 0; index < values.length; index += 1) {
            parts.push(encodeURIComponent(name) + "=" + encodeURIComponent(values[index].value));
        }
    }

    return parts.length === 0 ? location : location + "?" + parts.join("&");
}

function handler(event) {
    var request = event.request;
    var location;

    if (request.uri === "/resume/") {
        location = "/about.html";
    } else if (request.uri === "/programming/") {
        location = "/projects.html";
    } else if (request.uri === "/design/") {
        location = "/projects.html";
    } else {
        return request;
    }

    return {
        statusCode: 308,
        statusDescription: "Permanent Redirect",
        headers: {
            location: {
                value: appendQueryString(location, request.querystring || {})
            }
        }
    };
}
