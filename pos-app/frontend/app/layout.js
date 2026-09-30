import './globals.css';

export const metadata = {
  title: 'Step4 POS | レジ',
  description: '販売取引を登録するPOSレジ',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
