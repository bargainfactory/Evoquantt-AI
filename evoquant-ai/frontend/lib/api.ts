import axios, { type AxiosInstance } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let _instance: AxiosInstance | null = null;

export function getApiClient(): AxiosInstance {
  if (_instance) return _instance;
  _instance = axios.create({ baseURL: `${API_URL}/api` });
  _instance.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });
  _instance.interceptors.response.use(
    (r) => r,
    async (error) => {
      if (error.response?.status === 401 && typeof window !== "undefined") {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try {
            const res = await axios.post(`${API_URL}/api/auth/refresh`, { refresh_token: refresh });
            localStorage.setItem("access_token", res.data.access_token);
            error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
            return axios(error.config);
          } catch {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
        }
      }
      return Promise.reject(error);
    }
  );
  return _instance;
}

export const api = {
  // Auth
  login: (email: string, password: string, totp_code?: string) =>
    getApiClient().post("/auth/login", { email, password, totp_code }),
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    getApiClient().post("/auth/register", data),
  getMe: () => getApiClient().get("/auth/me"),
  setup2fa: () => getApiClient().post("/auth/2fa/setup"),
  confirm2fa: (code: string) => getApiClient().post("/auth/2fa/confirm", { code }),

  // Market Data
  getQuote: (symbol: string) => getApiClient().get(`/market/quote/${symbol}`),
  getOHLCV: (symbol: string, period = "1y", interval = "1d") =>
    getApiClient().get(`/market/ohlcv/${symbol}`, { params: { period, interval } }),
  getIndicators: (symbol: string, period = "1y") =>
    getApiClient().get(`/market/indicators/${symbol}`, { params: { period } }),
  getMlPredict: (symbol: string) => getApiClient().get(`/market/ml-predict/${symbol}`),
  getSentiment: (symbol: string) => getApiClient().get(`/market/sentiment/${symbol}`),
  getMacro: () => getApiClient().get("/market/macro"),
  searchSymbols: (q: string) => getApiClient().get("/market/search", { params: { q } }),
  getNews: (symbol: string) => getApiClient().get(`/market/news/${symbol}`),

  // Trading
  placeOrder: (order: Record<string, unknown>) => getApiClient().post("/trading/order", order),
  getOrders: (params?: Record<string, unknown>) => getApiClient().get("/trading/orders", { params }),
  cancelOrder: (id: string) => getApiClient().delete(`/trading/order/${id}/cancel`),
  getPositions: () => getApiClient().get("/trading/positions"),

  // Portfolio
  getPortfolioSummary: () => getApiClient().get("/portfolio/summary"),
  getPortfolioPositions: () => getApiClient().get("/portfolio/positions"),
  getPortfolioHistory: (days = 30) => getApiClient().get("/portfolio/history", { params: { days } }),
  getRiskMetrics: () => getApiClient().get("/portfolio/risk-metrics"),
  getAllocation: () => getApiClient().get("/portfolio/allocation"),

  // Options
  priceOption: (data: Record<string, unknown>) => getApiClient().post("/options/price", data),
  getOptionsChain: (symbol: string, expiry?: string) =>
    getApiClient().get(`/options/chain/${symbol}`, { params: { expiry } }),
  getIVSurface: (symbol: string) => getApiClient().get(`/options/iv-surface/${symbol}`),
  monteCarlo: (data: Record<string, unknown>) => getApiClient().post("/options/monte-carlo", data),
  strategyPnl: (legs: unknown[], spot_min: number, spot_max: number) =>
    getApiClient().post("/options/strategy-pnl", legs, { params: { spot_min, spot_max } }),
  suggestStrategy: (symbol: string, params: Record<string, unknown>) =>
    getApiClient().get(`/options/suggest/${symbol}`, { params }),

  // Recursive Sell
  runRecursiveSell: (config: Record<string, unknown>) => getApiClient().post("/recursive-sell/run", config),
  getRecursiveSellJob: (jobId: string) => getApiClient().get(`/recursive-sell/job/${jobId}`),
  getRecursiveSellResult: (jobId: string) => getApiClient().get(`/recursive-sell/result/${jobId}`),
  getConvergence: (jobId: string) => getApiClient().get(`/recursive-sell/convergence/${jobId}`),
  getRecursionTree: (jobId: string) => getApiClient().get(`/recursive-sell/tree/${jobId}`),

  // Evolution Lab
  runEvolution: (config: Record<string, unknown>) => getApiClient().post("/evolution/run", config),
  getEvolutionJob: (jobId: string) => getApiClient().get(`/evolution/job/${jobId}`),
  getLeaderboard: () => getApiClient().get("/evolution/leaderboard"),

  // DEX
  uniswapQuote: (data: Record<string, unknown>) => getApiClient().post("/dex/uniswap/quote", data),
  uniswapBuildSwap: (data: Record<string, unknown>) => getApiClient().post("/dex/uniswap/build-swap", data),
  jupiterQuote: (data: Record<string, unknown>) => getApiClient().post("/dex/jupiter/quote", data),
  jupiterSwap: (data: Record<string, unknown>) => getApiClient().post("/dex/jupiter/swap", data),
  jupiterPrice: (tokens: string, vs?: string) => getApiClient().get("/dex/jupiter/price", { params: { tokens, vs } }),
  getBestRoute: (chain: string, token_in: string, token_out: string, amount: string) =>
    getApiClient().get("/dex/best-route", { params: { chain, token_in, token_out, amount } }),

  // Brokers
  connectBroker: (data: Record<string, unknown>) => getApiClient().post("/brokers/connect", data),
  listBrokers: () => getApiClient().get("/brokers/list"),
  getBrokerBalances: (broker: string) => getApiClient().get(`/brokers/${broker}/balances`),

  // Wallets
  connectWallet: (data: Record<string, unknown>) => getApiClient().post("/wallets/connect", data),
  listWallets: () => getApiClient().get("/wallets/list"),
  getWalletBalance: (chain: string, address: string) => getApiClient().get(`/wallets/balance/${chain}/${address}`),

  // Alerts
  createAlert: (data: Record<string, unknown>) => getApiClient().post("/alerts/", data),
  listAlerts: () => getApiClient().get("/alerts/"),
  deleteAlert: (id: string) => getApiClient().delete(`/alerts/${id}`),
  toggleAlert: (id: string) => getApiClient().patch(`/alerts/${id}/toggle`),

  // Backtest
  runBacktest: (config: Record<string, unknown>) => getApiClient().post("/backtest/run", config),
  getBacktestJob: (jobId: string) => getApiClient().get(`/backtest/job/${jobId}`),

  // AI Copilot
  askEvo: (message: string, context?: Record<string, unknown>, symbol?: string) =>
    getApiClient().post("/ai/ask", { message, context, symbol }),
  getAiSuggestions: (symbol: string) => getApiClient().get(`/ai/suggestions/${symbol}`),
};

export default api;
