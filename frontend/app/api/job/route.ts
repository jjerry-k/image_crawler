import { NextRequest } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

export async function DELETE(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.toString();
    const backendUrl = query
      ? `${buildBackendUrl("/request/job")}?${query}`
      : buildBackendUrl("/request/job");
    const response = await fetch(backendUrl, {
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
