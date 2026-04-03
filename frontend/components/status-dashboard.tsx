"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { JobGallery } from "@/components/job-gallery";
import type { CrawlItem, CrawlStatus, DeleteResponse, StatusResponse } from "@/lib/types";

const STATUS_SECTIONS: Array<{ key: CrawlStatus; title: string }> = [
  { key: "Ready", title: "대기" },
  { key: "Proceeding", title: "처리중" },
  { key: "Success", title: "완료" },
  { key: "Fail", title: "실패" },
];

const EMPTY_COUNTS = {
  Ready: 0,
  Proceeding: 0,
  Success: 0,
  Fail: 0,
};

function formatTimestamp(value?: string) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

async function parseJson<T>(response: Response): Promise<T | null> {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function StatusColumn({
  title,
  statusKey,
  items,
  onOpenGallery,
}: {
  title: string;
  statusKey: CrawlStatus;
  items: CrawlItem[];
  onOpenGallery: (item: CrawlItem) => void;
}) {
  return (
    <section className="panel status-panel">
      <div className="status-panel-head">
        <h2>{title}</h2>
        <span>{items.length}건</span>
      </div>

      {items.length === 0 ? (
        <p className="empty-copy">현재 표시할 항목이 없습니다.</p>
      ) : (
        <ul className="job-list">
          {items.map((item) => {
            const key = `${item.date}-${item.key_class}-${item.keyword}-${item.class_path}`;

            return (
              <li key={key} className={`job-card status-${item.crawled.toLowerCase()}`}>
                <div className="job-card-head">
                  <strong>{item.keyword}</strong>
                  <span>{item.key_class}</span>
                </div>
                <dl className="job-meta">
                  <div>
                    <dt>등록일</dt>
                    <dd>{item.date}</dd>
                  </div>
                  <div>
                    <dt>최근 갱신</dt>
                    <dd>{formatTimestamp(item.updated_at)}</dd>
                  </div>
                </dl>
                {statusKey === "Fail" ? (
                  <div className="job-failure">
                    <strong>실패 사유</strong>
                    <p title={item.error_message ?? "실패 사유가 기록되지 않았습니다."}>
                      {item.error_message ?? "실패 사유가 기록되지 않았습니다."}
                    </p>
                  </div>
                ) : null}
                {item.crawled === "Success" ? (
                  <div className="job-card-actions">
                    <button type="button" className="secondary-button" onClick={() => onOpenGallery(item)}>
                      사진 보기
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function StatusDashboard({
  autoRefreshSeconds,
}: {
  autoRefreshSeconds: number;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const safePathname = pathname ?? "/status";

  const testMode = searchParams?.get("test") === "true";
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [galleryItem, setGalleryItem] = useState<CrawlItem | null>(null);
  const hasStatusData = Boolean(status);

  useEffect(() => {
    let ignore = false;

    async function loadStatus() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await fetch(`/api/status?test=${testMode}`, {
          cache: "no-store",
        });
        const payload = await parseJson<StatusResponse>(response);

        if (!response.ok || payload?.MSG !== "Success") {
          throw new Error(payload?.error ?? "상태를 불러오지 못했습니다.");
        }

        if (ignore) {
          return;
        }

        setStatus(payload);
        setLastRefreshedAt(new Date().toISOString());
      } catch (error) {
        if (!ignore) {
          setErrorMessage(error instanceof Error ? error.message : "상태 조회 중 오류가 발생했습니다.");
          setStatus(null);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    void loadStatus();

    return () => {
      ignore = true;
    };
  }, [refreshNonce, testMode]);

  useEffect(() => {
    if (!autoRefresh || autoRefreshSeconds <= 0) {
      return;
    }

    const timerId = window.setInterval(() => {
      setRefreshNonce((value) => value + 1);
    }, autoRefreshSeconds * 1000);

    return () => {
      window.clearInterval(timerId);
    };
  }, [autoRefresh, autoRefreshSeconds]);

  const counts = status?.counts ?? EMPTY_COUNTS;
  const sections = STATUS_SECTIONS.map((section) => ({
    ...section,
    items: status?.items.filter((item) => item.crawled === section.key) ?? [],
  }));

  const switchMode = (nextTestMode: boolean) => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    if (nextTestMode) {
      params.set("test", "true");
    } else {
      params.delete("test");
    }

    const nextQuery = params.toString();
    router.replace(nextQuery ? `${safePathname}?${nextQuery}` : safePathname);
    setGalleryItem(null);
    setNoticeMessage(null);
    setRefreshNonce((value) => value + 1);
  };

  const handleDelete = async () => {
    if (!window.confirm("Ready 상태의 작업만 초기화합니다. 계속하시겠습니까?")) {
      return;
    }

    setIsDeleting(true);
    setErrorMessage(null);
    setNoticeMessage(null);

    try {
      const response = await fetch(`/api/delete?test=${testMode}`, {
        method: "POST",
        cache: "no-store",
      });
      const payload = await parseJson<DeleteResponse>(response);

      if (!response.ok || payload?.MSG !== "Success") {
        throw new Error(payload?.error ?? "대기열 초기화에 실패했습니다.");
      }

      setNoticeMessage(`삭제 완료: ${payload.deleted ?? 0}건`);
      setRefreshNonce((value) => value + 1);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "대기열 초기화 중 오류가 발생했습니다.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <main className="page">
      <section className="hero compact">
        <p className="eyebrow">Queue Status</p>
        <h1 className="hero-title">크롤링 진행 현황</h1>
        <p className="hero-copy">
          현재 모드: <strong>{testMode ? "테스트" : "실서비스"}</strong>
          {lastRefreshedAt ? ` · 최근 갱신 ${formatTimestamp(lastRefreshedAt)}` : ""}
        </p>
      </section>

      <section className="panel controls-panel">
        <div className="mode-switch" role="group" aria-label="Mode selector">
          <button
            type="button"
            className={`switch-button ${!testMode ? "active" : ""}`}
            onClick={() => switchMode(false)}
            aria-pressed={!testMode}
          >
            실서비스
          </button>
          <button
            type="button"
            className={`switch-button ${testMode ? "active" : ""}`}
            onClick={() => switchMode(true)}
            aria-pressed={testMode}
          >
            테스트
          </button>
        </div>

        <div className="controls-row">
          <label className="checkbox-row" htmlFor="auto-refresh">
            <input
              id="auto-refresh"
              type="checkbox"
              checked={autoRefresh}
              onChange={(event) => setAutoRefresh(event.target.checked)}
            />
            <span>{autoRefreshSeconds}초 자동 새로고침</span>
          </label>

          <div className="button-row">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setRefreshNonce((value) => value + 1)}
            >
              지금 새로고침
            </button>
            <button
              type="button"
              className="danger-button"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "초기화 중..." : "대기열 초기화"}
            </button>
          </div>
        </div>

        {noticeMessage ? (
          <div className="message-banner success" role="status" aria-live="polite">
            {noticeMessage}
          </div>
        ) : null}
        {errorMessage ? (
          <div className="message-banner error" role="alert">
            {errorMessage}
          </div>
        ) : null}
      </section>

      <section className="metrics-grid">
        <article className="panel metric-card">
          <span>대기</span>
          <strong>{hasStatusData ? counts.Ready : "-"}</strong>
        </article>
        <article className="panel metric-card">
          <span>처리중</span>
          <strong>{hasStatusData ? counts.Proceeding : "-"}</strong>
        </article>
        <article className="panel metric-card">
          <span>완료</span>
          <strong>{hasStatusData ? counts.Success : "-"}</strong>
        </article>
        <article className="panel metric-card">
          <span>실패</span>
          <strong>{hasStatusData ? counts.Fail : "-"}</strong>
        </article>
        <article className="panel metric-card">
          <span>큐 크기</span>
          <strong>{hasStatusData ? status?.queue_size ?? 0 : "-"}</strong>
        </article>
      </section>

      {isLoading && !status ? (
        <section className="panel loading-panel">상태를 불러오는 중입니다.</section>
      ) : null}

      {!isLoading && errorMessage && !status ? (
        <section className="panel status-error-panel">
          <h2>상태를 불러오지 못했습니다.</h2>
          <p>{errorMessage}</p>
        </section>
      ) : (
        <section className="status-grid">
          {sections.map((section) => (
            <StatusColumn
              key={section.key}
              title={section.title}
              statusKey={section.key}
              items={section.items}
              onOpenGallery={setGalleryItem}
            />
          ))}
        </section>
      )}

      {galleryItem ? (
        <JobGallery
          item={galleryItem}
          testMode={testMode}
          onClose={() => setGalleryItem(null)}
          onJobDeleted={() => {
            setGalleryItem(null);
            setRefreshNonce((value) => value + 1);
          }}
        />
      ) : null}
    </main>
  );
}
