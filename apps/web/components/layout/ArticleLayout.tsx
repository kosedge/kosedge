import Container from "./Container";

export default function ArticleLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <Container>
      <article className="mx-auto max-w-3xl py-16">
        <header className="mb-10">
          <h1 className="text-4xl font-extrabold leading-tight text-white">
            {title}
          </h1>

          {subtitle && (
            <p className="mt-4 text-lg text-white/70">
              {subtitle}
            </p>
          )}
        </header>

        <div className="prose prose-invert prose-lg max-w-none">
          {children}
        </div>
      </article>
    </Container>
  );
}