import React, { useEffect, useRef, useState } from 'react';

export const AUTH_STORAGE_KEY = 'prism_auth';
const DEFAULT_PASSWORD = 'prism';

type LoginGateProps = {
  onSuccess: () => void;
};

export const LoginGate = ({ onSuccess }: LoginGateProps) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const expectedPassword = (import.meta.env.VITE_LOGIN_PASSWORD || DEFAULT_PASSWORD).trim();
  const canSubmit = password.length > 0;

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!password) {
      setError('请输入密码');
      return;
    }
    if (password === expectedPassword) {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(AUTH_STORAGE_KEY, '1');
      }
      onSuccess();
      return;
    }
    setError('密码错误');
    setPassword('');
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-amber-50 via-white to-teal-50 relative overflow-hidden">
      <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-teal-200/50 blur-3xl" />
      <div className="absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-amber-200/50 blur-3xl" />
      <div className="relative z-10 flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white/90 p-8 shadow-2xl backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary-600 text-white flex items-center justify-center font-semibold shadow-md shadow-primary-200">
              P
            </div>
            <div>
              <div className="text-xl font-semibold text-zinc-900 tracking-tight">Prism 登录</div>
              <div className="text-sm text-zinc-500">请输入访问密码后进入</div>
            </div>
          </div>
          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-700" htmlFor="login-password">
                登录密码
              </label>
              <input
                id="login-password"
                ref={inputRef}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (error) setError('');
                }}
                className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-900 shadow-sm transition focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-200"
                placeholder="请输入密码"
              />
              {error ? (
                <div className="text-sm text-rose-600">{error}</div>
              ) : (
                <div className="text-xs text-zinc-400">密码大小写敏感</div>
              )}
            </div>
            <button
              type="submit"
              disabled={!canSubmit}
              className={`w-full rounded-xl px-4 py-3 text-sm font-semibold transition ${
                canSubmit
                  ? 'bg-primary-600 text-white shadow-sm shadow-primary-200 hover:bg-primary-700'
                  : 'bg-zinc-200 text-zinc-500 cursor-not-allowed'
              }`}
            >
              进入系统
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
