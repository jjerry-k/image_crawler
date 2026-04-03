import { NextRequest } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  proxyBinaryResponse,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

function buildRequestUrl(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  return query ? `${buildBackendUrl("/request/image")}?${query}` : buildBackendUrl("/request/image");
}

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(buildRequestUrl(request), {
      method: "GET",
      cache: "no-store",
      headers: {
        accept: "*/*",
      },
    });

    if ((response.headers.get("content-type") ?? "").includes("application/json")) {
      return proxyJsonResponse(response);
    }

    return proxyBinaryResponse(response);
  } catch (error) {
    return backendUnavailableResponse(error);
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const response = await fetch(buildRequestUrl(request), {
      method: "DELETE",
      cache: "no-store",
      headers: {
        accept: "application/json",
      },
    });

    return proxyJsonResponse(response);
  } catch (error) {
    return backendUnavailableResponse(error);
  }
}
