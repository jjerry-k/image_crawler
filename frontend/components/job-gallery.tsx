"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type {
  CrawlItem,
  ImageDeleteResponse,
  ImageItem,
  ImageListResponse,
  JobDeleteResponse,
} from "@/lib/types";

function formatBytes(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

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

function buildJobSearchParams(item: CrawlItem, testMode: boolean) {
  return new URLSearchParams({
    date: item.date,
    key_class: item.key_class,
    keyword: item.keyword,
    class_path: item.class_path,
    test: String(testMode),
  });
}

function buildDownloadHref(item: CrawlItem, testMode: boolean, names: string[] = []) {
  const params = buildJobSearchParams(item, testMode);
  names.forEach((name) => params.append("name", name));
  return `/api/download?${params.toString()}`;
}

export function JobGallery({
  item,
  testMode,
  onClose,
  onJobDeleted,
}: {
  item: CrawlItem;
  testMode: boolean;
  onClose: () => void;
  onJobDeleted: () => void;
}) {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [selectedNames, setSelectedNames] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeletingJob, setIsDeletingJob] = useState(false);
  const [pendingDeleteNames, setPendingDeleteNames] = useState<string[]>([]);
  const [isDeletingSelection, setIsDeletingSelection] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);

  const jobQuery = useMemo(() => buildJobSearchParams(item, testMode).toString(), [item, testMode]);
  const downloadAllHref = useMemo(() => buildDownloadHref(item, testMode), [item, testMode]);
  const selectedDownloadHref = useMemo(() => {
    if (selectedNames.length === 0) {
      return null;
    }
    return buildDownloadHref(item, testMode, selectedNames);
  }, [item, selectedNames, testMode]);
  const selectedImage = images.find((image) => image.name === selectedName) ?? images[0] ?? null;
  const selectedCount = selectedNames.length;

  useEffect(() => {
    panelRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  useEffect(() => {
    let ignore = false;

    async function loadImages() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await fetch(`/api/images?${jobQuery}`, {
          cache: "no-store",
        });
        const payload = await parseJson<ImageListResponse>(response);

        if (!response.ok || payload?.MSG !== "Success") {
          throw new Error(payload?.error ?? "이미지 목록을 불러오지 못했습니다.");
        }

        if (ignore) {
          return;
        }

        const nextImages = payload.images ?? [];
        setImages(nextImages);
        setSelectedName((current) => {
          if (current && nextImages.some((image) => image.name === current)) {
            return current;
          }
          return nextImages[0]?.name ?? null;
        });
        setSelectedNames((current) => current.filter((name) => nextImages.some((image) => image.name === name)));
      } catch (error) {
        if (!ignore) {
          setErrorMessage(error instanceof Error ? error.message : "이미지 목록 조회 중 오류가 발생했습니다.");
          setImages([]);
          setSelectedName(null);
          setSelectedNames([]);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    void loadImages();

    return () => {
      ignore = true;
    };
  }, [jobQuery]);

  useEffect(() => {
    if (!selectedName && images.length > 0) {
      setSelectedName(images[0].name);
      return;
    }

    if (selectedName && !images.some((image) => image.name === selectedName)) {
      setSelectedName(images[0]?.name ?? null);
    }
  }, [images, selectedName]);

  const isDeletingName = (name: string) => pendingDeleteNames.includes(name);

  const toggleImageSelection = (name: string) => {
    setSelectedNames((current) =>
      current.includes(name) ? current.filter((value) => value !== name) : [...current, name],
    );
  };

  const handleSelectAll = () => {
    setSelectedNames(images.map((image) => image.name));
  };

  const handleClearSelection = () => {
    setSelectedNames([]);
  };

  const deleteImages = async (names: string[]) => {
    if (names.length === 0) {
      return;
    }

    const message =
      names.length === 1
        ? `이미지 ${names[0]} 파일을 삭제하시겠습니까?`
        : `선택한 이미지 ${names.length}개를 삭제하시겠습니까?`;
    if (!window.confirm(message)) {
      return;
    }

    const params = buildJobSearchParams(item, testMode);
    names.forEach((name) => params.append("name", name));

    setPendingDeleteNames(names);
    setIsDeletingSelection(names.length > 1);
    setErrorMessage(null);
    setNoticeMessage(null);

    try {
      const response = await fetch(`/api/image?${params.toString()}`, {
        method: "DELETE",
        cache: "no-store",
      });
      const payload = await parseJson<ImageDeleteResponse>(response);

      if (!response.ok || payload?.MSG !== "Success") {
        throw new Error(payload?.error ?? "이미지 삭제에 실패했습니다.");
      }

      const deletedNames =
        payload?.names && payload.names.length > 0
          ? payload.names
          : payload?.name
            ? [payload.name]
            : names;

      setImages((current) => current.filter((image) => !deletedNames.includes(image.name)));
      setSelectedNames((current) => current.filter((name) => !deletedNames.includes(name)));
      setNoticeMessage(
        deletedNames.length === 1
          ? `이미지 삭제 완료: ${deletedNames[0]}`
          : `${deletedNames.length}개 이미지 삭제가 완료됐습니다.`,
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "이미지 삭제 중 오류가 발생했습니다.");
    } finally {
      setPendingDeleteNames([]);
      setIsDeletingSelection(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!window.confirm("이 작업의 수집 이미지와 상태 기록을 모두 삭제합니다. 계속하시겠습니까?")) {
      return;
    }

    setIsDeletingJob(true);
    setErrorMessage(null);
    setNoticeMessage(null);

    try {
      const response = await fetch(`/api/job?${jobQuery}`, {
        method: "DELETE",
        cache: "no-store",
      });
      const payload = await parseJson<JobDeleteResponse>(response);

      if (!response.ok || payload?.MSG !== "Success") {
        throw new Error(payload?.error ?? "작업 삭제에 실패했습니다.");
      }

      onJobDeleted();
      onClose();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "작업 삭제 중 오류가 발생했습니다.");
    } finally {
      setIsDeletingJob(false);
    }
  };

  const handleDownloadSelected = () => {
    if (!selectedDownloadHref) {
      return;
    }

    window.location.assign(selectedDownloadHref);
  };

  return (
    <div className="gallery-overlay" role="dialog" aria-modal="true" aria-labelledby="gallery-title">
      <button type="button" className="gallery-backdrop" onClick={onClose} aria-label="갤러리 닫기" />

      <section ref={panelRef} className="gallery-panel" tabIndex={-1}>
        <div className="gallery-head">
          <div>
            <p className="section-kicker">Collected Images</p>
            <h2 id="gallery-title">
              {item.key_class} / {item.keyword}
            </h2>
            <p className="section-copy">
              모드: {testMode ? "테스트" : "실서비스"} · 파일 {images.length}개
              {selectedCount > 0 ? ` · 선택 ${selectedCount}개` : ""}
            </p>
          </div>

          <div className="gallery-head-actions">
            <a href={downloadAllHref} className="secondary-button">
              전체 다운로드
            </a>
            <button type="button" className="danger-button" onClick={handleDeleteJob} disabled={isDeletingJob}>
              {isDeletingJob ? "삭제 중..." : "작업 삭제"}
            </button>
            <button type="button" className="ghost-button" onClick={onClose}>
              닫기
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

        <div className="gallery-body">
          <section className="panel gallery-preview-panel">
            {isLoading ? (
              <p className="loading-panel">이미지를 불러오는 중입니다.</p>
            ) : selectedImage ? (
              <>
                <div className="gallery-preview-head">
                  <div>
                    <strong>{selectedImage.name}</strong>
                    <p>
                      {formatBytes(selectedImage.size)} · {formatTimestamp(selectedImage.modified_at)}
                    </p>
                  </div>
                  <div className="button-row">
                    <a
                      href={`/api/image?${jobQuery}&name=${encodeURIComponent(selectedImage.name)}&download=true`}
                      className="secondary-button"
                    >
                      파일 다운로드
                    </a>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => void deleteImages([selectedImage.name])}
                      disabled={isDeletingSelection || isDeletingName(selectedImage.name)}
                    >
                      {isDeletingName(selectedImage.name) ? "삭제 중..." : "이 사진 삭제"}
                    </button>
                  </div>
                </div>

                <div className="gallery-preview-frame">
                  <img
                    src={`/api/image?${jobQuery}&name=${encodeURIComponent(selectedImage.name)}`}
                    alt={`${item.keyword} ${selectedImage.name}`}
                    className="gallery-preview-image"
                  />
                </div>
              </>
            ) : (
              <p className="empty-copy">표시할 이미지가 없습니다.</p>
            )}
          </section>

          <section className="panel gallery-list-panel">
            <div className="status-panel-head">
              <h2>파일 목록</h2>
              <span>{images.length}건</span>
            </div>

            <div className="gallery-selection-bar">
              <p className="gallery-selection-summary">
                선택 {selectedCount} / 전체 {images.length}
              </p>
              <div className="button-row">
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handleSelectAll}
                  disabled={images.length === 0 || selectedCount === images.length}
                >
                  전체 선택
                </button>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={handleClearSelection}
                  disabled={selectedCount === 0}
                >
                  선택 해제
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleDownloadSelected}
                  disabled={!selectedDownloadHref}
                >
                  선택 다운로드
                </button>
                <button
                  type="button"
                  className="danger-button"
                  onClick={() => void deleteImages(selectedNames)}
                  disabled={selectedCount === 0 || isDeletingSelection}
                >
                  {isDeletingSelection ? "선택 삭제 중..." : "선택 삭제"}
                </button>
              </div>
            </div>

            {isLoading ? (
              <p className="loading-panel">썸네일을 준비하는 중입니다.</p>
            ) : images.length === 0 ? (
              <p className="empty-copy">현재 저장된 이미지가 없습니다.</p>
            ) : (
              <ul className="gallery-grid">
                {images.map((image) => {
                  const isActive = selectedImage?.name === image.name;
                  const isSelected = selectedNames.includes(image.name);

                  return (
                    <li
                      key={image.name}
                      className={`gallery-tile ${isActive ? "active" : ""} ${isSelected ? "selected" : ""}`}
                    >
                      <div className="gallery-tile-head">
                        <label className="gallery-checkbox">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleImageSelection(image.name)}
                            aria-label={`${image.name} 선택`}
                          />
                          <span>선택</span>
                        </label>
                      </div>

                      <button
                        type="button"
                        className="gallery-thumb-button"
                        onClick={() => setSelectedName(image.name)}
                        aria-pressed={isActive}
                      >
                        <img
                          src={`/api/image?${jobQuery}&name=${encodeURIComponent(image.name)}`}
                          alt={image.name}
                          className="gallery-thumb-image"
                          loading="lazy"
                        />
                      </button>
                      <div className="gallery-tile-meta">
                        <strong title={image.name}>{image.name}</strong>
                        <span>
                          {formatBytes(image.size)} · {formatTimestamp(image.modified_at)}
                        </span>
                      </div>
                      <div className="gallery-tile-actions">
                        <a
                          href={`/api/image?${jobQuery}&name=${encodeURIComponent(image.name)}&download=true`}
                          className="mini-link"
                        >
                          다운로드
                        </a>
                        <button
                          type="button"
                          className="mini-danger"
                          onClick={() => void deleteImages([image.name])}
                          disabled={isDeletingSelection || isDeletingName(image.name)}
                        >
                          {isDeletingName(image.name) ? "삭제 중" : "삭제"}
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}
