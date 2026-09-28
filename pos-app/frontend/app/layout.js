export const metadata = {
  title: 'Step4 POS',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body style={{ fontFamily: 'sans-serif', margin: '1rem' }}>{children}</body>
    </html>
  );
}
