'use client';

import { useMemo, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function Home() {
  const [staffId, setStaffId] = useState('STAFF001');
  const [password, setPassword] = useState('password');
  const [loggedIn, setLoggedIn] = useState(false);
  const [memberId, setMemberId] = useState('');
  const [memberMessage, setMemberMessage] = useState('非会員取引');
  const [barcode, setBarcode] = useState('');
  const [items, setItems] = useState([]);
  const [quote, setQuote] = useState(null);
  const [message, setMessage] = useState('');

  const selectedCode = useMemo(() => (items[0] ? items[0].product_code : ''), [items]);

  const authFetch = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    return res;
  };

  const recalc = async (nextItems, customerId) => {
    if (nextItems.length === 0) {
      setQuote(null);
      return;
    }
    const res = await authFetch('/api/purchase/quote', {
      method: 'POST',
      body: JSON.stringify({ items: nextItems, customer_id: customerId || null }),
    });
    if (!res.ok) {
      const body = await res.json();
      setQuote(null);
      setMessage(body.message || '計算に失敗しました');
      return;
    }
    setQuote(await res.json());
  };

  const doLogin = async (e) => {
    e.preventDefault();
    const res = await authFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ staff_id: staffId, password }),
    });
    if (!res.ok) {
      setMessage('ログインに失敗しました');
      return;
    }
    setLoggedIn(true);
    setMessage('ログインしました');
  };

  const lookupMember = async () => {
    if (!memberId) {
      setMemberMessage('非会員取引');
      await recalc(items, null);
      return;
    }
    const res = await authFetch(`/api/customers/${encodeURIComponent(memberId)}`);
    if (!res.ok) {
      const body = await res.json();
      setMessage(body.message || '会員照合に失敗しました');
      return;
    }
    const body = await res.json();
    setMemberMessage(body.message);
    await recalc(items, body.found ? memberId : null);
  };

  const addByBarcode = async () => {
    const code = barcode.trim();
    if (!code) return;

    const current = [...items];
    const index = current.findIndex((i) => i.product_code === code);
    if (index >= 0) {
      current[index] = { ...current[index], quantity: current[index].quantity + 1 };
    } else {
      current.push({ product_code: code, quantity: 1 });
    }
    setItems(current);
    setBarcode('');
    await recalc(current, memberMessage === '会員を確認しました' ? memberId : null);
  };

  const confirmPurchase = async () => {
    if (!quote) return;
    const res = await authFetch('/api/purchase/confirm', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: memberMessage === '会員を確認しました' ? memberId : null,
        items,
        client_total_amount: quote.total_amount,
      }),
    });
    const body = await res.json();
    if (!res.ok) {
      setMessage(body.message || '会計に失敗しました');
      return;
    }
    setMessage(`会計完了: 取引ID ${body.purchase_id}`);
    setItems([]);
    setQuote(null);
  };

  if (!loggedIn) {
    return (
      <main>
        <h1>簡易POS（Lv2）</h1>
        <form onSubmit={doLogin}>
          <p>
            <label>スタッフID <input value={staffId} onChange={(e) => setStaffId(e.target.value)} /></label>
          </p>
          <p>
            <label>パスワード <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          </p>
          <button type="submit">ログイン</button>
        </form>
        <p>{message}</p>
      </main>
    );
  }

  return (
    <main>
      <h1>簡易POS（Lv2）</h1>
      <p>会員: {memberMessage}</p>
      <p>
        <label>会員ID <input value={memberId} onChange={(e) => setMemberId(e.target.value)} /></label>
        <button type="button" onClick={lookupMember}>照合</button>
      </p>
      <p>
        <label>バーコード <input value={barcode} onChange={(e) => setBarcode(e.target.value)} /></label>
        <button type="button" onClick={addByBarcode}>追加</button>
      </p>
      <p>選択状態（フロント管理）: {selectedCode || '未選択'}</p>
      <ul>
        {items.map((item) => (
          <li key={item.product_code}>{item.product_code} x {item.quantity}</li>
        ))}
      </ul>
      {quote && (
        <section>
          <h2>会計</h2>
          <p>小計(税抜): {quote.subtotal_excl_tax} 円</p>
          <p>税額: {quote.tax_amount} 円</p>
          <p>合計: {quote.total_amount} 円</p>
          <button type="button" onClick={confirmPurchase}>購入確定</button>
        </section>
      )}
      <p>{message}</p>
      <p>カメラスキャンが利用できない場合はバーコード手入力を利用してください。</p>
    </main>
  );
}
