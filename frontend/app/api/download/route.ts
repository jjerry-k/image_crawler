import { NextRequest } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  proxyBinaryResponse,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.toString();
    const backendUrl = query
      ? `${buildBackendUrl("/request/download")}?${query}`
      : buildBackendUrl("/request/download");
    const response = await fetch(backendUrl, {
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
