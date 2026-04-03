export type CrawlStatus = "Ready" | "Proceeding" | "Success" | "Fail";

export interface CrawlResponse {
  MSG: string;
  queued?: number;
  error?: string;
}

export interface DeleteResponse {
  MSG: string;
  deleted?: number;
  error?: string;
}

export interface CrawlItem {
  date: string;
  key_class: string;
  keyword: string;
  class_path: string;
  storage_path?: string;
  storage_dir?: string;
  crawled: CrawlStatus;
  updated_at?: string;
  error_message?: string;
  downloaded_images?: number;
}

export interface ImageItem {
  name: string;
  size: number;
  modified_at?: string;
  mime_type?: string;
}

export interface ImageListResponse {
  MSG: string;
  item?: CrawlItem;
  images: ImageItem[];
  test: boolean;
  error?: string;
}

export interface ImageDeleteResponse {
  MSG: string;
  deleted?: boolean;
  name?: string;
  names?: string[];
  deleted_count?: number;
  remaining?: number;
  error?: string;
}

export interface JobDeleteResponse {
  MSG: string;
  deleted?: boolean;
  error?: string;
}

export interface StatusResponse {
  MSG: string;
  counts: Record<CrawlStatus, number>;
  items: CrawlItem[];
  queue_size: number;
  test: boolean;
  error?: string;
}
