"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useState } from "react";

import type { CrawlResponse } from "@/lib/types";

function formatBytes(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

async function parseJson<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function UploadForm() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const statusHref = testMode ? "/status?test=true" : "/status";

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    setSuccessMessage(null);
    setErrorMessage(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedFile) {
      setErrorMessage("업로드할 엑셀 파일을 선택해 주세요.");
      setSuccessMessage(null);
      return;
    }

    setIsSubmitting(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("test", String(testMode));

      const response = await fetch("/api/crawl", {
        method: "POST",
        body: formData,
      });
      const payload = await parseJson<CrawlResponse>(response);

      if (!response.ok || payload?.MSG !== "Success") {
        throw new Error(payload?.error ?? "작업 등록에 실패했습니다.");
      }

      setSuccessMessage(`작업 등록 완료: ${payload.queued ?? 0}개`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="panel upload-panel">
      <div className="panel-head">
        <p className="section-kicker">Queue Submit</p>
        <h2>엑셀 업로드</h2>
        <p className="section-copy">backend에 직접 붙는 대신, Next 서버가 업로드를 검증하고 내부로 전달합니다.</p>
      </div>

      <form className="stack-form" onSubmit={handleSubmit}>
        <label className="field-label" htmlFor="crawl-file">
          크롤링 목록 파일
        </label>
        <input
          id="crawl-file"
          className="file-input"
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileChange}
        />

        <div className="file-summary">
          {selectedFile ? (
            <>
              <strong>{selectedFile.name}</strong>
              <span>{formatBytes(selectedFile.size)}</span>
            </>
          ) : (
            <span>선택된 파일이 없습니다.</span>
          )}
        </div>

        <label className="checkbox-row" htmlFor="test-mode">
          <input
            id="test-mode"
            type="checkbox"
            checked={testMode}
            onChange={(event) => setTestMode(event.target.checked)}
          />
          <span>테스트 모드로 작업 등록</span>
        </label>

        <div className="button-row">
          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? "등록 중..." : "크롤링 시작"}
          </button>
          <Link href={statusHref} className="secondary-button">
            처리 현황 보기
          </Link>
        </div>

        {successMessage ? <div className="message-banner success">{successMessage}</div> : null}
        {errorMessage ? <div className="message-banner error">{errorMessage}</div> : null}
      </form>
    </section>
  );
}
