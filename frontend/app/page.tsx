import { MobileShell } from "@/components/mobile-shell";
import { getAppBootstrap } from "@/lib/api";

export default async function HomePage() {
  const bootstrap = await getAppBootstrap();

  return (
    <main className="flex min-h-dvh items-center justify-center bg-frame sm:px-6 sm:py-8">
      <MobileShell bootstrap={bootstrap} />
    </main>
  );
}
