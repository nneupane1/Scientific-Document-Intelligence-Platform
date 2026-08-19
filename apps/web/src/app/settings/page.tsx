export default function SettingsPage() {
  return (
    <main className="shell narrow">
      <section className="page-heading">
        <p className="eyebrow">Runtime</p>
        <h1>Local processing settings</h1>
        <p>Universal scientific processing is active in the local API. <code>SCIDOC_*</code> environment variables can override the built-in policy when needed.</p>
      </section>
      <div className="settings-grid">
        <article className="panel"><h2>Resolution cascade</h2><p>300 DPI baseline, 450 DPI retry, 600 DPI maximum.</p></article>
        <article className="panel"><h2>Engine policy</h2><p>Native extraction → lightweight OCR / formula model → review.</p></article>
        <article className="panel capability-settings">
          <h2>Universal document analysis</h2>
          <p>All supported scientific content is enabled by default. Every detected region is preserved in SDR with source coordinates, confidence, and provenance.</p>
          <div className="capability-list" aria-label="Enabled processing capabilities">
            {["Mathematics", "Physics & engineering", "Computing, AI & ML", "Life & medical sciences", "Finance & quantitative", "Tables & charts", "Chemistry", "Braille accessibility", "Visual analysis"].map((capability) => <span key={capability}><i aria-hidden />{capability}</span>)}
          </div>
        </article>
      </div>
    </main>
  );
}
