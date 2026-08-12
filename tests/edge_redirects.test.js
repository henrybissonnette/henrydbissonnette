"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const sourcePath = path.join(__dirname, "..", "infra", "aws", "terraform", "main", "edge_redirects.js");
const context = vm.createContext({});
vm.runInContext(`${fs.readFileSync(sourcePath, "utf8")}\nthis.edgeHandler = handler;`, context, {
    filename: sourcePath,
});

function request(uri, querystring = {}) {
    return { uri, querystring, headers: { host: { value: "example.cloudfront.net" } } };
}

const redirects = [
    ["/resume/", "/about.html"],
    ["/programming/", "/projects.html"],
    ["/design/", "/projects.html"],
];

for (const [from, to] of redirects) {
    test(`${from} redirects permanently to ${to} without an empty query suffix`, () => {
        const result = context.edgeHandler({ request: request(from) });
        assert.equal(result.statusCode, 308);
        assert.equal(result.statusDescription, "Permanent Redirect");
        assert.equal(result.headers.location.value, to);
        assert.ok(result.headers.location.value.startsWith("/"));
    });

    test(`${from} preserves populated, repeated, and empty query values`, () => {
        const querystring = {
            source: { value: "portfolio" },
            topic: { multiValue: [{ value: "storage" }, { value: "aws & dns" }] },
            empty: { value: "" },
        };
        const result = context.edgeHandler({ request: request(from, querystring) });
        assert.equal(
            result.headers.location.value,
            `${to}?source=portfolio&topic=storage&topic=aws%20%26%20dns&empty=`,
        );
    });
}

for (const uri of ["/resume", "/resume//", "/Resume/", "/programming/x", "/design", "/", "/about.html"]) {
    test(`${uri} passes through unchanged`, () => {
        const original = request(uri, { keep: { value: "yes" } });
        const result = context.edgeHandler({ request: original });
        assert.strictEqual(result, original);
    });
}
