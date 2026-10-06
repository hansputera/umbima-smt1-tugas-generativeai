import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, roleHome, verifyToken } from "@/lib/token";

export default function proxy(request: NextRequest) {
  const session = verifyToken(request.cookies.get(SESSION_COOKIE)?.value);
  const { pathname } = request.nextUrl;

  if (pathname === "/login") {
    if (session) {
      return NextResponse.redirect(new URL(roleHome(session.role), request.url));
    }
    return NextResponse.next();
  }

  if (pathname === "/") {
    const target = session ? roleHome(session.role) : "/login";
    return NextResponse.redirect(new URL(target, request.url));
  }

  if (!session) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }

  const segment = pathname.split("/")[1];
  if (
    (segment === "admin" ||
      segment === "lecturer" ||
      segment === "student") &&
    segment !== session.role
  ) {
    return NextResponse.redirect(new URL(roleHome(session.role), request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
