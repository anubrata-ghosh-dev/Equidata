interface BiasAlertProps {
  message?: string;
}

export default function BiasAlert({ message = "This decision may be influenced by sensitive attributes" }: BiasAlertProps) {
  return (
    <div className="fade-in rounded-xl border border-danger/50 bg-danger/10 p-4 text-danger shadow-[0_0_0_1px_rgba(244,63,94,0.2)]">
      <p className="text-sm font-semibold">⚠️ {message}</p>
    </div>
  );
}
