'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export default function Home() {
  const [staffId, setStaffId] = useState('STAFF001');
  const [password, setPassword] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [staff, setStaff] = useState(null);
  const [memberId, setMemberId] = useState('');
  const [activeMemberId, setActiveMemberId] = useState(null);
  const [memberName, setMemberName] = useState('');
  const [memberState, setMemberState] = useState('guest');
  const [barcode, setBarcode] = useState('');
  const [items, setItems] = useState([]);
  const [quote, setQuote] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState('');
  const [scannerTarget, setScannerTarget] = useState(null);
  const [scannerRetry, setScannerRetry] = useState(0);
  const [cameraState, setCameraState] = useState('idle');
  const [cameraError, setCameraError] = useState('');
  const videoRef = useRef(null);
  const scannerActionsRef = useRef(null);

  useEffect(() => {
    let isCurrent = true;
    fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' })
      .then((res) => res.ok ? res.json() : null)
      .then((result) => {
        if (isCurrent && result) {
          setStaff(result);
          setLoggedIn(true);
        }
      })
      .catch(() => {});
    return () => { isCurrent = false; };
  }, []);

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
      return true;
    }
    try {
      const res = await authFetch('/api/purchase/quote', {
        method: 'POST',
        body: JSON.stringify({ items: nextItems, customer_id: customerId || null }),
      });
      if (!res.ok) {
        setQuote(null);
        setNotice({ tone: 'error', text: await responseMessage(res, '金額を計算できませんでした') });
        return false;
      }
      setQuote(await res.json());
      return true;
    } catch {
      setQuote(null);
      setNotice({ tone: 'error', text: '金額を計算できませんでした。通信状態を確認してください。' });
      return false;
    }
  };

  const responseMessage = async (res, fallback) => {
    try {
      const body = await res.json();
      return body.message || fallback;
    } catch {
      return fallback;
    }
  };

  const doLogin = async (e) => {
    e.preventDefault();
    setBusy('login');
    setNotice(null);
    try {
      const res = await authFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ staff_id: staffId, password }),
      });
      if (!res.ok) {
        setNotice({ tone: 'error', text: await responseMessage(res, 'ログインできませんでした') });
        return;
      }
      setStaff(await res.json());
      setLoggedIn(true);
      setNotice(null);
    } catch {
      setNotice({ tone: 'error', text: 'サーバーに接続できませんでした。時間をおいて再度お試しください。' });
    } finally {
      setBusy('');
    }
  };

  const lookupMember = async (e, memberValue = memberId) => {
    e?.preventDefault();
    setBusy('member');
    setNotice(null);
    const normalizedMemberId = memberValue.trim();
    try {
      if (!normalizedMemberId) {
        setActiveMemberId(null);
        setMemberName('');
        setMemberState('guest');
        if (await recalc(items, null)) setNotice({ tone: 'neutral', text: '非会員取引に設定しました' });
        return;
      }
      const res = await authFetch(`/api/customers/${encodeURIComponent(normalizedMemberId)}`);
      if (!res.ok) {
        setNotice({ tone: 'error', text: await responseMessage(res, '会員を照合できませんでした') });
        return;
      }
      const result = await res.json();
      if (!result.found) {
        setActiveMemberId(null);
        setMemberName('');
        setMemberState('missing');
        if (await recalc(items, null)) setNotice({ tone: 'neutral', text: '会員が見つかりません。非会員取引として続行できます。' });
        return;
      }
      setActiveMemberId(normalizedMemberId);
      setMemberName(result.name);
      setMemberState('found');
      if (await recalc(items, normalizedMemberId)) setNotice({ tone: 'success', text: `${result.name} さんを確認しました` });
    } catch {
      setNotice({ tone: 'error', text: '会員を照合できませんでした。通信状態を確認してください。' });
    } finally {
      setBusy('');
    }
  };

  const addByBarcode = async (e, barcodeValue = barcode) => {
    e?.preventDefault();
    const code = barcodeValue.trim();
    if (!code || busy) return;

    const current = [...items];
    const index = current.findIndex((i) => i.product_code === code);
    if (index >= 0) {
      if (current[index].quantity >= 999) {
        setNotice({ tone: 'error', text: '1商品の登録上限（999点）に達しています' });
        return;
      }
      current[index] = { ...current[index], quantity: current[index].quantity + 1 };
    } else {
      current.push({ product_code: code, quantity: 1 });
    }
    setBusy('cart');
    setNotice(null);
    try {
      const valid = await recalc(current, activeMemberId);
      if (valid) {
        setItems(current);
        setBarcode('');
        setNotice({ tone: 'success', text: '商品を登録しました' });
      }
    } catch {
      setNotice({ tone: 'error', text: '商品を登録できませんでした。通信状態を確認してください。' });
    } finally {
      setBusy('');
    }
  };

  const changeQuantity = async (productCode, change) => {
    if (busy) return;
    const current = items
      .map((item) => item.product_code === productCode ? { ...item, quantity: item.quantity + change } : item)
      .filter((item) => item.quantity > 0);
    setBusy('cart');
    setNotice(null);
    try {
      if (await recalc(current, activeMemberId)) setItems(current);
    } catch {
      setNotice({ tone: 'error', text: '数量を変更できませんでした。通信状態を確認してください。' });
    } finally {
      setBusy('');
    }
  };

  const removeItem = async (productCode) => {
    if (busy) return;
    const current = items.filter((item) => item.product_code !== productCode);
    setBusy('cart');
    setNotice(null);
    try {
      if (await recalc(current, activeMemberId)) setItems(current);
    } catch {
      setNotice({ tone: 'error', text: '商品を削除できませんでした。通信状態を確認してください。' });
    } finally {
      setBusy('');
    }
  };

  const confirmPurchase = async () => {
    if (!quote || busy) return;
    setBusy('confirm');
    setNotice(null);
    try {
      const res = await authFetch('/api/purchase/confirm', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: activeMemberId,
          items,
          client_total_amount: quote.total_amount,
        }),
      });
      if (!res.ok) {
        setNotice({ tone: 'error', text: await responseMessage(res, '取引を確定できませんでした') });
        return;
      }
      const result = await res.json();
      setItems([]);
      setQuote(null);
      setMemberId('');
      setActiveMemberId(null);
      setMemberName('');
      setMemberState('guest');
      setNotice({ tone: 'success', text: `取引 ${result.purchase_id} を確定しました` });
    } catch {
      setNotice({ tone: 'error', text: '取引を確定できませんでした。通信状態を確認してください。' });
    } finally {
      setBusy('');
    }
  };

  const logout = async () => {
    setBusy('logout');
    try {
      await authFetch('/api/auth/logout', { method: 'POST' });
    } finally {
      setLoggedIn(false);
      setStaff(null);
      setItems([]);
      setQuote(null);
      setActiveMemberId(null);
      setMemberId('');
      setMemberName('');
      setMemberState('guest');
      setPassword('');
      setNotice(null);
      setBusy('');
    }
  };

  const openScanner = (target) => {
    setCameraError('');
    setCameraState('loading');
    setScannerTarget(target);
  };

  const closeScanner = () => {
    setScannerTarget(null);
    setCameraError('');
    setCameraState('idle');
  };

  useEffect(() => {
    scannerActionsRef.current = { lookupMember, addByBarcode };
  });

  useEffect(() => {
    if (!scannerTarget) return undefined;

    let isActive = true;
    let controls;
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') closeScanner();
    };
    document.addEventListener('keydown', closeOnEscape);

    import('@zxing/browser')
      .then(async ({ BrowserMultiFormatReader }) => {
        if (!isActive || !videoRef.current) return;
        try {
          const reader = new BrowserMultiFormatReader();
          controls = await reader.decodeFromVideoDevice(undefined, videoRef.current, (result) => {
            if (!result || !isActive) return;
            const value = result.getText().trim();
            if (!value) return;

            isActive = false;
            controls?.stop();
            setScannerTarget(null);
            setCameraState('idle');
            if (scannerTarget === 'member') {
              setMemberId(value);
              setMemberState('pending');
              scannerActionsRef.current?.lookupMember(null, value);
            } else {
              setBarcode(value);
              scannerActionsRef.current?.addByBarcode(null, value);
            }
          });
          if (isActive) setCameraState('ready');
          else controls.stop();
        } catch (error) {
          if (!isActive) return;
          const message = error?.name === 'NotAllowedError' || error?.name === 'SecurityError'
            ? 'カメラへのアクセスが許可されていません。ブラウザーの設定をご確認ください。'
            : error?.name === 'NotFoundError'
              ? '利用できるカメラが見つかりません。'
              : error?.name === 'NotReadableError'
                ? 'カメラを起動できません。他のアプリで使用中でないかご確認ください。'
                : 'カメラを起動できませんでした。ブラウザーのカメラ設定をご確認ください。';
          setCameraError(message);
          setCameraState('error');
        }
      })
      .catch(() => {
        if (isActive) {
          setCameraError('読み取り機能を起動できませんでした。ページを再読み込みしてください。');
          setCameraState('error');
        }
      });

    return () => {
      isActive = false;
      controls?.stop();
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [scannerTarget, scannerRetry]);

  if (!loggedIn) {
    return (
      <main className="login-page">
        <section className="login-panel">
          <div className="brand-mark" aria-hidden="true">S4</div>
          <p className="eyebrow">STEP4 / REGISTER</p>
          <h1>レジをはじめる</h1>
          <p className="login-caption">スタッフ情報を入力してください</p>
          <form className="login-form" onSubmit={doLogin}>
            <label className="field-label" htmlFor="staff-id">スタッフID</label>
            <input id="staff-id" autoComplete="username" value={staffId} onChange={(e) => setStaffId(e.target.value)} required />
            <label className="field-label" htmlFor="password">パスワード</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {notice && <p className={`notice notice-${notice.tone}`} role="alert">{notice.text}</p>}
            <button className="button button-primary login-submit" type="submit" disabled={busy === 'login'}>
              {busy === 'login' ? '確認中...' : 'ログイン'}
              <span aria-hidden="true">→</span>
            </button>
          </form>
          <p className="login-footnote">販売管理システム <span>·</span> 店舗レジ</p>
        </section>
      </main>
    );
  }

  return (
    <main className="register-page">
      <header className="topbar">
        <div className="topbar-inner">
          <Link className="brand" href="/" aria-label="Step4 POS ホーム">
            <span className="brand-mark" aria-hidden="true">S4</span>
            <span><strong>STEP4</strong><small>REGISTER</small></span>
          </Link>
          <div className="session-tools">
            <span className="session-status"><span className="status-dot" /> 稼働中</span>
            <span className="staff-chip"><strong>{staff?.name || staff?.staff_id}</strong><small>{staff?.staff_id}</small></span>
            <button className="button button-quiet" type="button" onClick={logout} disabled={busy === 'logout'}>
              {busy === 'logout' ? '終了中...' : 'ログアウト'}
            </button>
          </div>
        </div>
      </header>

      <div className="register-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">SALES / NEW TRANSACTION</p>
            <h1>販売登録</h1>
          </div>
          <div className="transaction-tag"><span>取引</span><strong>新規</strong></div>
        </div>

        <nav className="flow-steps" aria-label="販売登録の流れ">
          <span className="flow-step is-current"><i>01</i><b>会員</b><small>任意</small></span>
          <span className="flow-rule" />
          <span className={`flow-step ${items.length ? 'is-current' : ''}`}><i>02</i><b>商品</b><small>{items.reduce((sum, item) => sum + item.quantity, 0)} 点</small></span>
          <span className="flow-rule" />
          <span className={`flow-step ${quote ? 'is-current' : ''}`}><i>03</i><b>会計</b><small>{quote ? '確認' : '待機'}</small></span>
        </nav>

        {notice && <div className={`notice notice-${notice.tone} page-notice`} role={notice.tone === 'error' ? 'alert' : 'status'} aria-live="polite">{notice.text}</div>}

        <div className="register-grid">
          <div className="workflow">
            <section className="workflow-section member-section">
              <div className="section-heading">
                <span className="section-number">01</span>
                <div><h2>会員確認</h2><p>会員価格を適用</p></div>
                <span className={`member-state ${activeMemberId ? 'member-active' : ''}`}>
                  {memberState === 'found' ? '確認済み' : memberState === 'missing' ? '該当なし' : memberState === 'pending' ? '未照合' : '非会員'}
                </span>
              </div>
              <form className="inline-form member-form" onSubmit={lookupMember}>
                <label className="sr-only" htmlFor="member-id">会員ID</label>
                <input
                  id="member-id"
                  placeholder="会員ID"
                  value={memberId}
                  onChange={(e) => {
                    const value = e.target.value;
                    setMemberId(value);
                    setMemberState(value.trim() ? 'pending' : 'guest');
                    if (activeMemberId) {
                      setActiveMemberId(null);
                      setMemberName('');
                      recalc(items, null);
                    }
                  }}
                />
                <button className="button button-camera" type="button" onClick={() => openScanner('member')} disabled={busy !== ''} aria-label="カメラで会員IDを読み取る">
                  カメラ
                </button>
                <button className="button button-secondary" type="submit" disabled={busy !== ''}>
                  {busy === 'member' ? '照合中...' : '会員を照合'}
                </button>
              </form>
              {activeMemberId && <p className="member-confirmation">{memberName} <span>·</span> {activeMemberId}</p>}
            </section>

            <section className="workflow-section product-section">
              <div className="section-heading">
                <span className="section-number">02</span>
                <div><h2>商品を登録</h2><p>商品コード</p></div>
              </div>
              <form className="inline-form product-form" onSubmit={addByBarcode}>
                <label className="sr-only" htmlFor="barcode">商品コード</label>
                <span className="scan-symbol" aria-hidden="true">⌗</span>
                <input
                  id="barcode"
                  autoFocus
                  placeholder="バーコードを入力"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                />
                <button className="button button-camera" type="button" onClick={() => openScanner('product')} disabled={busy !== ''} aria-label="カメラで商品バーコードを読み取る">
                  カメラ
                </button>
                <button className="button button-primary" type="submit" disabled={!barcode.trim() || busy !== ''}>
                  {busy === 'cart' ? '処理中...' : '商品を追加'}
                  <span aria-hidden="true">＋</span>
                </button>
              </form>
            </section>

            <section className="workflow-section cart-section">
              <div className="section-heading cart-heading">
                <span className="section-number">03</span>
                <div><h2>登録商品</h2><p>カートの内容</p></div>
                <span className="item-count">{items.reduce((sum, item) => sum + item.quantity, 0)} 点</span>
              </div>
              {items.length === 0 ? (
                <div className="empty-cart"><span aria-hidden="true">＋</span><p>商品はまだ登録されていません</p></div>
              ) : (
                <div className="cart-list" aria-busy={busy === 'cart'}>
                  {items.map((item, index) => {
                    const quoteItem = quote?.items.find((entry) => entry.product_code === item.product_code);
                    return (
                      <article className="cart-row" key={item.product_code}>
                        <span className="cart-index">{String(index + 1).padStart(2, '0')}</span>
                        <div className="cart-product">
                          <strong>{quoteItem?.product_name || '商品'}</strong>
                          <small>{item.product_code} · {quoteItem ? `${Number(quoteItem.discounted_price).toLocaleString('ja-JP')} 円 / 点` : '価格確認中'}</small>
                        </div>
                        <div className="quantity-control" aria-label={`${quoteItem?.product_name || item.product_code}の数量`}>
                          <button type="button" aria-label="数量を1減らす" onClick={() => changeQuantity(item.product_code, -1)} disabled={busy !== '' || item.quantity <= 1}>−</button>
                          <span>{item.quantity}</span>
                          <button type="button" aria-label="数量を1増やす" onClick={() => changeQuantity(item.product_code, 1)} disabled={busy !== '' || item.quantity >= 999}>＋</button>
                        </div>
                        <strong className="line-total">{quoteItem ? `${Number(quoteItem.final_amount).toLocaleString('ja-JP')} 円` : '—'}</strong>
                        <button className="remove-button" type="button" onClick={() => removeItem(item.product_code)} disabled={busy !== ''} aria-label={`${quoteItem?.product_name || item.product_code}を削除`}>削除</button>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>

          <aside className="summary-panel" aria-label="会計概要">
            <div className="summary-heading"><span>03 / CHECKOUT</span><h2>会計</h2></div>
            <div className="summary-customer">
              <span>お客様</span>
              <strong>{activeMemberId ? memberName : '非会員'}</strong>
            </div>
            <div className="summary-lines">
              <div><span>商品点数</span><strong>{items.reduce((sum, item) => sum + item.quantity, 0)} 点</strong></div>
              <div><span>小計（税抜）</span><strong>{quote ? `${Number(quote.subtotal_excl_tax).toLocaleString('ja-JP')} 円` : '—'}</strong></div>
              <div><span>消費税 {quote ? `(${Number(quote.tax_rate * 100).toLocaleString('ja-JP')}%)` : ''}</span><strong>{quote ? `${Number(quote.tax_amount).toLocaleString('ja-JP')} 円` : '—'}</strong></div>
            </div>
            <div className="summary-total"><span>お会計合計</span><strong>{quote ? Number(quote.total_amount).toLocaleString('ja-JP') : '0'}<small>円</small></strong></div>
            <button className="button button-checkout" type="button" onClick={confirmPurchase} disabled={!quote || busy !== ''}>
              {busy === 'confirm' ? '確定中...' : '取引を確定'}
              <span aria-hidden="true">→</span>
            </button>
            <p className="summary-footnote">{quote ? '内容を確認して取引を確定してください' : '商品を登録すると合計が表示されます'}</p>
          </aside>
        </div>
        <footer className="page-footer"><span>STEP4 POS</span><span>SALES MANAGEMENT</span></footer>
      </div>
      {scannerTarget && (
        <div className="scanner-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) closeScanner(); }}>
          <section className="scanner-dialog" role="dialog" aria-modal="true" aria-labelledby="scanner-title">
            <header className="scanner-header">
              <div>
                <p className="eyebrow">{scannerTarget === 'member' ? 'MEMBER / SCAN' : 'PRODUCT / SCAN'}</p>
                <h2 id="scanner-title">{scannerTarget === 'member' ? '会員IDを読み取る' : '商品バーコードを読み取る'}</h2>
              </div>
              <button className="scanner-close" type="button" onClick={closeScanner} aria-label="カメラを閉じる">×</button>
            </header>
            <div className={`scanner-view ${cameraState === 'ready' ? 'scanner-ready' : ''}`}>
              <video ref={videoRef} autoPlay muted playsInline />
              <span className="scan-reticle" aria-hidden="true" />
              {cameraState === 'loading' && <div className="camera-message">カメラに接続しています...</div>}
              {cameraState === 'error' && <div className="camera-message camera-message-error">{cameraError}</div>}
            </div>
            <div className="scanner-footer">
              {cameraState === 'error' ? (
                <>
                  <button className="button button-secondary" type="button" onClick={() => { setCameraError(''); setCameraState('loading'); setScannerRetry((retry) => retry + 1); }}>再試行</button>
                  <button className="button button-primary" type="button" onClick={closeScanner}>閉じる</button>
                </>
              ) : (
                <button className="button button-secondary" type="button" onClick={closeScanner}>読み取りを終了</button>
              )}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
