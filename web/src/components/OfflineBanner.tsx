import { useState, useEffect } from "react";

export default function OfflineBanner({ fetchedAt }: { fetchedAt: Date | null }) {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (online || !fetchedAt) return null;

  const ts = fetchedAt.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="offline-banner">
      Offline — showing data from {ts}
    </div>
  );
}
