import assert from "node:assert/strict";
import { request as httpRequest } from "node:http";
import test from "node:test";

const origin = "http://localhost:3000";
const applicationOrigin = "http://app.localhost:3000";

function request(path, host, options) {
  // Connect to loopback explicitly; OS DNS support for *.localhost varies outside browsers.
  return new Promise((resolve, reject) => {
    const outgoing = httpRequest(`${origin}${path}`, {
      method: options.method,
      headers: { ...options.headers, host },
    }, (incoming) => {
      const chunks = [];
      incoming.on("data", (chunk) => chunks.push(chunk));
      incoming.on("error", reject);
      incoming.on("end", () => {
        const headers = new Headers();
        for (const [name, values] of Object.entries(incoming.headers)) {
          for (const value of Array.isArray(values) ? values : [values]) {
            if (value !== undefined) headers.append(name, value);
          }
        }
        resolve(new Response(incoming.statusCode === 204 ? null : Buffer.concat(chunks), {
          status: incoming.statusCode,
          headers,
        }));
      });
    });
    outgoing.on("error", reject);
    outgoing.end(options.body);
  });
}

test("marketing stays public and links to the application", async () => {
  const response = await request("/", "localhost:3000", {});
  assert.equal(response.status, 200);
  const page = await response.text();
  assert.match(page, /borrow the moment/);
  assert.match(page, /href="http:\/\/app\.localhost:3000\/login"/);
  assert.match(page, /action="http:\/\/app\.localhost:3000\/search"/);
  assert.equal((page.match(/<header /g) ?? []).length, 1);
});

test("marketing serves the Plus membership page", async () => {
  const response = await request("/plus", "localhost:3000", {});
  assert.equal(response.status, 200);
  const page = await response.text();
  assert.match(page, /PassIt Plus/);
  assert.match(page, /Eco Saver/);
  assert.match(page, /Mega Saver/);
  assert.equal((page.match(/<header /g) ?? []).length, 1);
});

test("application root renders search, not marketing", async () => {
  const response = await request("/?q=camera", "app.localhost:3000", {});
  assert.equal(response.status, 200);
  const page = await response.text();
  assert.doesNotMatch(page, /borrow the moment/);
  assert.equal((page.match(/<header /g) ?? []).length, 1);
});

test("old application links redirect to the app host with queries intact", async () => {
  for (const path of ["/search?q=camera&mrt=Bugis", "/login?next=%2Fbookings", "/bookings/123"]) {
    const response = await request(path, "localhost:3000", {});
    assert.equal(response.status, 307);
    assert.equal(response.headers.get("location"), `${applicationOrigin}${path}`);
  }
});

test("application routes remain directly accessible", async () => {
  for (const path of ["/login", "/signup", "/search", "/bookings", "/listings/new", "/dashboard/lender"]) {
    const response = await request(path, "app.localhost:3000", {});
    assert.equal(response.status, 200, path);
    assert.equal((await response.text()).match(/<header /g)?.length, 1, path);
  }
});

test("same-origin API supports login, session, uploads, and logout", async () => {
  const host = "app.localhost:3000";
  const anonymous = await request("/v1/auth/me", host, {});
  assert.equal(anonymous.status, 401);

  const login = await request("/v1/auth/session", host, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: "seed-01@passit.demo", password: "passit-demo-2026" }),
  });
  assert.equal(login.status, 200);
  const sessionCookie = login.headers.get("set-cookie");
  assert.match(sessionCookie, /HttpOnly/i);
  assert.doesNotMatch(sessionCookie, /Domain=/i);
  const cookie = sessionCookie.split(";")[0];

  const session = await request("/v1/auth/me", host, { headers: { cookie } });
  assert.equal(session.status, 200);

  const presign = await request("/v1/media/presign", host, {
    method: "POST",
    headers: { cookie, "content-type": "application/json" },
    body: JSON.stringify({ stage: "listing", content_type: "image/png" }),
  });
  assert.equal(presign.status, 200);
  const upload = await presign.json();
  assert.equal(new URL(upload.upload_url).origin, applicationOrigin);
  const uploadUrl = new URL(upload.upload_url);
  const image = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=", "base64");
  const uploaded = await request(`${uploadUrl.pathname}${uploadUrl.search}`, host, {
    method: "PUT",
    headers: upload.headers,
    body: image,
  });
  assert.equal(uploaded.status, 200);
  const downloaded = await request(uploadUrl.pathname, host, {});
  assert.equal(downloaded.status, 200);
  assert.deepEqual(Buffer.from(await downloaded.arrayBuffer()), image);

  const logout = await request("/v1/auth/session", host, { method: "DELETE", headers: { cookie } });
  assert.equal(logout.status, 204);
  assert.match(logout.headers.get("set-cookie"), /Max-Age=0/i);
});
