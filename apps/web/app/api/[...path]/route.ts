import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.API_URL || "http://127.0.0.1:8000";

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  const path = (params.path || []).join("/");
  const targetUrl = `${BACKEND_URL}/api/${path}${request.nextUrl.search}`;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("host", new URL(BACKEND_URL).host);
  requestHeaders.delete("content-length");

  try {
    const hasBody = !["GET", "HEAD"].includes(request.method);
    const body = hasBody ? await request.blob() : undefined;

    const res = await fetch(targetUrl, {
      method: request.method,
      headers: requestHeaders,
      body,
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "set-cookie") {
        responseHeaders.append(key, value);
      }
    });

    // Forward Set-Cookie header(s) correctly using getSetCookie if available
    const cookies = typeof res.headers.getSetCookie === "function"
      ? res.headers.getSetCookie()
      : (res.headers.get("set-cookie") ? [res.headers.get("set-cookie")!] : []);

    for (const cookieStr of cookies) {
      responseHeaders.append("set-cookie", cookieStr);
    }

    const data = await res.arrayBuffer();

    return new NextResponse(data, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    return NextResponse.json(
      {
        detail:
          "Backend RECLAIM engine server is offline. Please ensure FastAPI server is running on port 8000.",
      },
      { status: 503 }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
