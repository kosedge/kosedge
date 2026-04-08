// apps/web/lib/test-utils.tsx
import { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { SessionProvider } from "next-auth/react";
import { UserRole } from "#prisma";

// Mock session for testing
const mockSession = {
  user: {
    id: "test-user-id",
    email: "test@example.com",
    name: "Test User",
    role: UserRole.USER,
  },
  expires: "2025-12-31",
};

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  session?: typeof mockSession;
}

const AllTheProviders = ({
  children,
  session = mockSession,
}: {
  children: React.ReactNode;
  session?: typeof mockSession;
}) => {
  return <SessionProvider session={session}>{children}</SessionProvider>;
};

const customRender = (ui: ReactElement, options?: CustomRenderOptions) => {
  const { session, ...renderOptions } = options || {};

  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProviders session={session}>{children}</AllTheProviders>
    ),
    ...renderOptions,
  });
};

export * from "@testing-library/react";
export { customRender as render };
