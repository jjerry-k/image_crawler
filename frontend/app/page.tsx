import Link from "next/link";

import { UploadForm } from "@/components/upload-form";

export default function HomePage() {
  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Next.js Frontend</p>
        <h1 className="hero-title">크롤링 작업을 등록하고 상태를 한 화면에서 추적합니다.</h1>
        <p className="hero-copy">
          엑셀 파일을 업로드하면 Flask backend에 작업이 등록됩니다. 브라우저는 Next.js API만 호출하고,
          실제 backend 통신은 서버에서 내부 프록시로 처리합니다.
        </p>
      </section>

      <section className="panel-grid">
        <UploadForm />

        <aside className="panel side-panel">
          <div className="panel-head">
            <p className="section-kicker">Input Guide</p>
            <h2>업로드 규칙</h2>
          </div>

          <div className="info-block">
            <h3>필수 컬럼</h3>
            <p>
              엑셀에는 <code>class</code>, <code>keyword</code> 컬럼이 있어야 합니다.
            </p>
          </div>

          <div className="info-block">
            <h3>키워드 형식</h3>
            <p>한 셀에 여러 키워드를 넣을 때는 쉼표로 구분합니다.</p>
          </div>

          <div className="info-block">
            <h3>상태 확인</h3>
            <p>등록 후에는 상태 페이지에서 대기, 처리중, 완료, 실패 항목을 바로 볼 수 있습니다.</p>
          </div>

          <Link href="/status" className="text-link">
            상태 페이지 바로가기
          </Link>
        </aside>
      </section>
    </main>
  );
}
