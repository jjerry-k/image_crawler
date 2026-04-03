import { Suspense } from "react";

import { StatusDashboard } from "@/components/status-dashboard";

export default function StatusPage() {
  const autoRefreshSeconds = Number(process.env.AUTO_REFRESH_SECONDS ?? 60);

  return (
    <Suspense
      fallback={
        <main className="page">
          <section className="panel loading-panel">상태 화면을 준비하는 중입니다.</section>
        </main>
      }
    >
      <StatusDashboard autoRefreshSeconds={autoRefreshSeconds} />
    </Suspense>
  );
}
