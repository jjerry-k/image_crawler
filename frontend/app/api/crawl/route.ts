import { NextResponse } from "next/server";

import {
  backendUnavailableResponse,
  buildBackendUrl,
  normalizeTestFlag,
  proxyJsonResponse,
} from "@/lib/backend";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const inboundFormData = await request.formData();
    const file = inboundFormData.get("file");

    if (!file || typeof file === "string") {
      return NextResponse.json(
        { MSG: "Failed", error: "file is required" },
        { status: 400 },
      );
    }

    const outboundFormData = new FormData();
    outboundFormData.append("file", file, file.name || "crawling.xlsx");
    outboundFormData.append("test", normalizeTestFlag(inboundFormData.get("test")));

    const response = await fetch(buildBackendUrl("/request/crawl"), {
      method: "POST",
      body: outboundFormData,
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
