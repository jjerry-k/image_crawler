import { NextRequest } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  getQueryTestFlag,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const test = getQueryTestFlag(request);
    const response = await fetch(`${buildBackendUrl("/request/status")}?test=${test}`, {
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
