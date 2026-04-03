import { NextRequest } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.toString();
    const backendUrl = query
      ? `${buildBackendUrl("/request/images")}?${query}`
      : buildBackendUrl("/request/images");
    const response = await fetch(backendUrl, {
      method: "GET",
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
