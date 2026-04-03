import { NextRequest, NextResponse } from "next/server";

const DEFAULT_BACKEND_BASE_URL = "http://backend:5000";

export function buildBackendUrl(path: string) {
  const baseUrl = (process.env.BACKEND_BASE_URL || DEFAULT_BACKEND_BASE_URL).replace(/\/$/, "");
  return `${baseUrl}/${path.replace(/^\//, "")}`;
}

export function normalizeTestFlag(value: FormDataEntryValue | string | null | undefined): "true" | "false" {
  if (typeof value !== "string") {
    return "false";
  }

  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase()) ? "true" : "false";
}

export function getQueryTestFlag(request: NextRequest): "true" | "false" {
  return normalizeTestFlag(request.nextUrl.searchParams.get("test"));
}

export async function proxyJsonResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  }

  const text = await response.text();
  return NextResponse.json(
    {
      MSG: response.ok ? "Success" : "Failed",
      error: text || "Unexpected backend response",
    },
    { status: response.status },
  );
}

export async function proxyBinaryResponse(response: Response) {
  const headers = new Headers();
  const passthroughHeaders = [
    "content-type",
    "content-disposition",
    "content-length",
    "cache-control",
    "last-modified",
  ];

  for (const headerName of passthroughHeaders) {
    const headerValue = response.headers.get(headerName);
    if (headerValue) {
      headers.set(headerName, headerValue);
    }
  }

  return new NextResponse(await response.arrayBuffer(), {
    status: response.status,
    headers,
  });
}

export function backendUnavailableResponse(error: unknown) {
  const message = error instanceof Error ? error.message : "Backend request failed";
  return NextResponse.json(
    {
      MSG: "Failed",
      error: message,
    },
    { status: 502 },
  );
}
