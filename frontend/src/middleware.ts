import { NextRequest, NextResponse } from "next/server";

/**
 * Protected routes that require an authenticated patient_id cookie.
 * Route groups (app) map to these top-level paths.
 */
const PROTECTED_PATHS = [
  "/today",
  "/coach",
  "/records",
  "/insights",
  "/care",
  "/me",
];

/** Auth paths — redirect to /today if already authenticated. */
const AUTH_PATHS = ["/login", "/onboarding"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const patientId = request.cookies.get("patient_id")?.value;

  const isProtected =
    pathname === "/" ||
    PROTECTED_PATHS.some(
      (p) => pathname === p || pathname.startsWith(p + "/"),
    );

  const isAuthPath = AUTH_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );

  // No cookie on a protected route → redirect to login
  if (isProtected && !patientId) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.search = "";
    return NextResponse.redirect(loginUrl);
  }

  // Has cookie and hits root → redirect to /today
  if (pathname === "/" && patientId) {
    const todayUrl = request.nextUrl.clone();
    todayUrl.pathname = "/today";
    todayUrl.search = "";
    return NextResponse.redirect(todayUrl);
  }

  // Has cookie and hits auth path → leave alone (Task 5 may redirect after login)
  void isAuthPath; // intentionally not redirecting; login page handles post-auth redirect

  return NextResponse.next();
}

export const config = {
  /*
   * Match all routes except:
   * - Next.js internals (_next/static, _next/image)
   * - API routes (/api/*)
   * - Public assets (favicon, images, etc.)
   */
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
