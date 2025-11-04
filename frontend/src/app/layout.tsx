import "./globals.css";

export const metadata = {
  title: "Local Research Assistant",
  description: "Self-hosted Letta-based knowledge assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
