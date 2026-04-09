import { redirect } from "next/navigation";

/**
 * Root route — server-side redirect to the Today screen.
 * Middleware handles the unauthenticated case and redirects to /login first.
 */
export default function Home() {
  redirect("/today");
}
