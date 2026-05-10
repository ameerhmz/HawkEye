import Link from "next/link";

export default function HomePage() {
  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-glow opacity-70" />
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-10 px-6 pb-20 pt-16">
        <header className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-ember text-ink font-display text-lg shadow-glow">
              H
            </span>
            <div className="text-sm uppercase tracking-[0.4em] text-sky/70">
              Hawk Eye
            </div>
          </div>
          <h1 className="font-display text-4xl leading-tight text-fog md:text-6xl">
            Intelligent Surveillance,
            <span className="block text-sky">locally powered.</span>
          </h1>
          <p className="max-w-2xl text-lg text-fog/70">
            Hawk Eye connects your phone cameras to a laptop-based AI engine.
            Monitor live feeds, receive instant alerts, and review activity with
            intelligent detection powered by advanced computer vision.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/monitor"
              className="rounded-full bg-ember px-6 py-3 font-display text-sm uppercase tracking-widest text-ink transition hover:translate-y-[-1px] hover:shadow-glow"
            >
              Launch Dashboard
            </Link>
            <Link
              href="/camera"
              className="rounded-full border border-fog/20 px-6 py-3 text-sm uppercase tracking-widest text-fog/70 transition hover:border-fog/40 hover:text-fog"
            >
              Connect Camera
            </Link>
          </div>
        </header>

        <section className="grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Phone-ready capture",
              body: "Browser-based camera nodes stream over WebRTC with fast reconnects."
            },
            {
              title: "Local AI detection",
              body: "YOLOv8 runs on your laptop for person detection and intrusion alerts."
            },
            {
              title: "Realtime timeline",
              body: "Events, clips, and alerts flow into a single live dashboard."
            }
          ].map((card) => (
            <div
              key={card.title}
              className="glass rounded-3xl p-6 text-fog/80 shadow-glow animate-rise"
            >
              <h3 className="font-display text-xl text-fog">{card.title}</h3>
              <p className="mt-2 text-sm text-fog/60">{card.body}</p>
            </div>
          ))}
        </section>

        <section className="glass rounded-3xl p-8 md:p-10">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl">
              <h2 className="font-display text-2xl text-fog">
                Ready for live monitoring
              </h2>
              <p className="mt-3 text-sm text-fog/60">
                Use a secure tunnel to connect Vercel to your local LiveKit and
                FastAPI endpoints. Keep AI and storage on your laptop, and scale
                as you grow.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky/20 text-sky animate-float">
                01
              </div>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-moss/20 text-moss animate-float">
                02
              </div>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-ember/20 text-ember animate-float">
                03
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
