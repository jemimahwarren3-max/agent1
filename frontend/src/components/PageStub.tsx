export function PageStub({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="flex h-full flex-col items-start justify-center gap-2">
      <h1 className="text-xl font-semibold text-white">{title}</h1>
      <p className="max-w-md text-sm text-white/50">
        This section is built in {phase} of the implementation plan. The navigation and layout
        are wired up now; the working feature lands once its backend endpoints exist.
      </p>
    </div>
  );
}
