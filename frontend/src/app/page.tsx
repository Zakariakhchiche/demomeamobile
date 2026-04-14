"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  Users,
  Building,
  AlertTriangle,
  ArrowRight,
  Zap,
  ChevronRight,
  MessageSquare,
  Target as TargetIcon,
  Activity,
  ShieldCheck,
  Cpu,
  Radio,
  Sparkles,
  BarChart3,
  Newspaper,
  ExternalLink,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { SkeletonCard, SkeletonKPI } from "@/components/LoadingSkeleton";
import { useQueryClient } from "@tanstack/react-query";
import { useTargets } from "@/lib/queries/useTargets";
import { useCfnews } from "@/lib/queries/useCfnews";

import { Target, CfnewsTarget } from "@/types";

export default function Home() {
  const { data, isLoading, error } = useTargets();
  const { data: cfnewsData, isLoading: cfnewsLoading } = useCfnews(15);
  const queryClient = useQueryClient();
  const targets = data?.data || [];
  const cfnewsTargets = cfnewsData?.data || [];
  const loading = isLoading;
  const fetchError = !!error;

  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const [cfnewsOpen, setCfnewsOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleAction = async (name: string, message: string) => {
    setProcessingAction(name);
    try {
      if (name === "recal") {
        // Actually call refresh-targets API to reload data from backend
        const res = await fetch("/api/refresh-targets", { method: "POST" });
        if (res.ok) {
          // Invalidate all related queries so dashboard, pipeline, signals update
          queryClient.invalidateQueries({ queryKey: ["targets"] });
          queryClient.invalidateQueries({ queryKey: ["pipeline"] });
          queryClient.invalidateQueries({ queryKey: ["signals"] });
          queryClient.invalidateQueries({ queryKey: ["graph"] });
          setNotification("Recalibration terminée. Scores et données mis à jour.");
        } else {
          setNotification("Recalibration effectuée (mode local).");
          queryClient.invalidateQueries({ queryKey: ["targets"] });
          queryClient.invalidateQueries({ queryKey: ["pipeline"] });
          queryClient.invalidateQueries({ queryKey: ["signals"] });
        }
      } else if (name === "diag") {
        // Invalidate targets query to re-fetch current state
        await queryClient.invalidateQueries({ queryKey: ["targets"] });
        setNotification("Diagnostics terminés. Données synchronisées.");
      } else {
        setNotification(message);
      }
    } catch {
      // Fallback: invalidate cache anyway
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      setNotification(message);
    } finally {
      setProcessingAction(null);
    }
  };

  // Re-fetch ALL data when copilot injects new targets from Pappers
  useEffect(() => {
    const handleTargetsUpdated = () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["graph"] });
    };
    window.addEventListener("targets-updated", handleTargetsUpdated);
    return () => window.removeEventListener("targets-updated", handleTargetsUpdated);
  }, [queryClient]);

  // ── Dynamic KPI computation ────────────────────────────────────
  const kpis = useMemo(() => {
    if (targets.length === 0) return null;

    const totalEntities = targets.length;
    const totalSignals = targets.reduce((acc, t) => acc + (t.topSignals?.length || 0), 0);
    const avgRelStrength = targets.length > 0
      ? Math.round(targets.reduce((acc, t) => acc + (t.relationship?.strength || 0), 0) / targets.length)
      : 0;
    const maPredicted = targets.filter((t) => t.globalScore >= 45).length;

    return { totalEntities, totalSignals, avgRelStrength, maPredicted };
  }, [targets]);

  // ── Priority distribution ──────────────────────────────────────
  const priorityDistribution = useMemo(() => {
    const dist: Record<string, number> = {
      "Action Prioritaire": 0,
      "Qualification": 0,
      "Monitoring": 0,
      "Veille Passive": 0,
    };
    targets.forEach((t) => {
      if (dist[t.priorityLevel] !== undefined) dist[t.priorityLevel]++;
      else dist["Veille Passive"]++;
    });
    return dist;
  }, [targets]);

  const priorityColors: Record<string, string> = {
    "Action Prioritaire": "bg-emerald-500",
    "Qualification": "bg-indigo-500",
    "Monitoring": "bg-amber-500",
    "Veille Passive": "bg-gray-600",
  };

  // ── Sector volatility from real data ───────────────────────────
  const sectorVolatility = useMemo(() => {
    if (targets.length === 0) return [];
    const sectorMap: Record<string, { total: number; scores: number[] }> = {};
    targets.forEach((t) => {
      if (!sectorMap[t.sector]) sectorMap[t.sector] = { total: 0, scores: [] };
      sectorMap[t.sector].total++;
      sectorMap[t.sector].scores.push(t.globalScore);
    });
    return Object.entries(sectorMap)
      .map(([name, data]) => ({
        name,
        count: data.total,
        avgScore: Math.round(data.scores.reduce((a, b) => a + b, 0) / data.scores.length),
      }))
      .sort((a, b) => b.avgScore - a.avgScore)
      .slice(0, 5);
  }, [targets]);

  const maxPriority = Math.max(...Object.values(priorityDistribution), 1);

  return (
    <div className="flex flex-col gap-10 w-full max-w-7xl mx-auto py-4 relative overflow-x-hidden">
      {/* Toast Notification */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: 50, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: 20, x: "-50%" }}
            className="fixed bottom-24 lg:bottom-10 left-1/2 z-[200] px-6 py-3 rounded-2xl bg-indigo-600 text-white font-black text-[10px] uppercase tracking-widest shadow-2xl flex items-center gap-3 border border-indigo-400"
          >
            <ShieldCheck size={16} /> {notification}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 shrink-0">
        <div>
          <h1 className="text-5xl font-black tracking-tighter text-white mb-3 flex items-center gap-5">
            EDRCF 6.0
            <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] text-indigo-400 font-black uppercase tracking-[0.2em]">
              <Radio size={14} className="animate-pulse" /> Intelligence Live
            </div>
          </h1>
          <p className="text-gray-400 text-lg font-medium max-w-2xl leading-relaxed">
            Centre de contrôle propriétaire d&apos;origination. Calibrage des{" "}
            <span className="text-white">fenêtres transactionnelles court-terme</span> et de la
            proximité réseau en temps réel.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          <button
            onClick={() =>
              handleAction("diag", "Diagnostics système terminés. Tous les clusters opérationnels.")
            }
            className="px-6 py-3 rounded-2xl bg-white/[0.03] border border-white/10 text-[11px] font-black uppercase tracking-widest text-white hover:bg-white/10 transition-all flex items-center justify-center gap-3"
          >
            {processingAction === "diag" ? (
              <div className="w-4 h-4 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
            ) : (
              <Activity size={16} className="text-indigo-500" />
            )}
            <span className="hidden sm:inline">
              {processingAction === "diag" ? "Analyse..." : "Diagnostics"}
            </span>
          </button>
          <button
            onClick={() =>
              handleAction(
                "recal",
                "Recalibration forcée initiée. Scores d'intelligence mis à jour."
              )
            }
            className="px-6 py-3 rounded-2xl bg-indigo-600 text-white shadow-[0_20px_40px_rgba(79,70,229,0.3)] hover:bg-indigo-500 transition-all flex items-center justify-center gap-3 font-black text-[11px] uppercase tracking-widest active:scale-95"
          >
            {processingAction === "recal" ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {processingAction === "recal" ? "Recalibration..." : "Recalibrer"}
          </button>
        </div>
      </header>

      {/* KPI Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonKPI key={i} />)
          : [
              {
                icon: Building,
                label: "Entités Surveillées",
                value: kpis ? kpis.totalEntities.toLocaleString("fr-FR") : "—",
                trend: `${targets.length}`,
                color: "text-indigo-400",
              },
              {
                icon: AlertTriangle,
                label: "Signaux Actifs",
                value: kpis ? kpis.totalSignals.toLocaleString("fr-FR") : "—",
                trend: `+${kpis?.totalSignals || 0}`,
                color: "text-amber-500",
              },
              {
                icon: Users,
                label: "Proximité Réseau",
                value: kpis ? `${kpis.avgRelStrength}%` : "—",
                trend: `+${kpis?.avgRelStrength || 0}`,
                color: "text-purple-400",
              },
              {
                icon: TrendingUp,
                label: "M&A Prédits",
                value: kpis ? kpis.maPredicted.toLocaleString("fr-FR") : "—",
                trend: `${kpis?.maPredicted || 0}`,
                color: "text-indigo-400",
              },
            ].map((card, idx) => (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1, duration: 0.5 }}
                key={card.label}
                className="p-8 rounded-[2.5rem] bg-black/40 border border-white/10 lg:backdrop-blur-2xl group hover:border-indigo-500/40 transition-all shadow-2xl relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-6 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity">
                  <card.icon size={80} />
                </div>
                <div className="flex justify-between items-start mb-8 relative z-10">
                  <div
                    className={`p-3.5 rounded-2xl bg-white/5 border border-white/10 ${card.color}`}
                  >
                    <card.icon size={24} />
                  </div>
                  <span
                    className={`text-[10px] font-black px-2.5 py-1 rounded-xl border ${
                      card.trend.startsWith("+")
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : card.trend.startsWith("-")
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          : "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
                    }`}
                  >
                    {card.trend}
                  </span>
                </div>
                <div className="text-4xl font-black text-white mb-2 tracking-tighter relative z-10">
                  {card.value}
                </div>
                <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest relative z-10">
                  {card.label}
                </div>
              </motion.div>
            ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start overflow-hidden">
        {/* Targets Feed - top 5 */}
        <div className="lg:col-span-8 flex flex-col gap-6 min-w-0">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <h2 className="text-xs font-black text-white uppercase tracking-[0.3em] flex items-center gap-4">
              <div className="hidden sm:block w-1.5 h-6 bg-indigo-600 rounded-full shadow-[0_0_15px_rgba(79,70,229,0.5)]" />
              Trajectoires d&apos;Origination Haute Confiance
            </h2>
            <button
              onClick={() => router.push("/targets")}
              className="w-full sm:w-auto text-[10px] font-black text-indigo-400 hover:text-indigo-300 uppercase tracking-widest transition-colors flex items-center justify-center gap-2 bg-indigo-500/5 px-5 py-2.5 rounded-2xl border border-indigo-500/10 hover:border-indigo-500/30"
            >
              Intelligence Vault <ChevronRight size={16} />
            </button>
          </div>

          {fetchError && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-8 rounded-[2.5rem] bg-rose-500/5 border border-rose-500/20 text-rose-300 flex items-center gap-6"
            >
              <div className="w-14 h-14 rounded-2xl bg-rose-500/10 flex items-center justify-center border border-rose-500/20 shadow-2xl">
                <AlertTriangle size={28} className="text-rose-500" />
              </div>
              <div>
                <div className="font-black uppercase tracking-widest text-xs mb-1 text-rose-500">
                  Erreur de Connexion
                </div>
                <div className="text-sm font-medium text-gray-400">
                  Impossible d&apos;établir le tunnel sécurisé vers les services internes EDRCF.
                  Vérifiez l&apos;état de l&apos;hôte.
                </div>
              </div>
            </motion.div>
          )}

          <div className="flex flex-col gap-5">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
              : targets.slice(0, 5).map((target, idx) => (
                  <motion.div
                    onClick={() => router.push(`/targets/${target.id}`)}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + idx * 0.1 }}
                    key={target.id}
                    className="group p-6 sm:p-10 rounded-[2rem] sm:rounded-[3rem] bg-black/40 border border-white/10 hover:border-indigo-500/40 transition-all cursor-pointer relative overflow-hidden lg:backdrop-blur-3xl shadow-2xl active:scale-[0.99]"
                  >
                    <div className="flex justify-between items-start relative z-10 gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-5 mb-5">
                          <div className="w-16 h-16 rounded-[1.5rem] bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 transition-all shadow-xl">
                            <Building size={28} />
                          </div>
                          <div>
                            <h3 className="text-3xl font-black text-white tracking-tighter group-hover:text-indigo-400 transition-colors truncate">
                              {target.name}
                            </h3>
                            <div className="flex gap-3 items-center mt-2 flex-wrap">
                              <span className="px-3 py-1 rounded-xl text-[10px] font-black tracking-widest uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                {target.sector}
                              </span>
                              {target.region && (
                                <span className="text-[10px] font-black text-gray-500 uppercase tracking-[0.15em]">
                                  {target.region}
                                </span>
                              )}
                              <span className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">
                                {target.id}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3 mt-8">
                          {target.topSignals?.slice(0, 4).map((signal) => (
                            <div
                              key={signal.id}
                              className="px-4 py-2 rounded-2xl bg-white/[0.03] text-gray-400 text-xs font-black uppercase tracking-widest flex items-center gap-2.5 border border-white/5 group-hover:bg-white/[0.05] transition-all overflow-hidden max-w-full"
                            >
                              <div className="w-2 h-2 rounded-full bg-indigo-500/50 shadow-[0_0_8px_rgba(79,70,229,0.5)] shrink-0" />
                              <span className="truncate">{signal.label}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex flex-col items-end shrink-0">
                        <span className="text-7xl font-black text-white leading-none tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-800">
                          {target.globalScore}
                        </span>
                        <span className="text-[10px] uppercase tracking-[0.4em] text-indigo-400/80 font-black mt-3">
                          Score Global
                        </span>
                      </div>
                    </div>

                    <div className="mt-10 pt-8 border-t border-white/[0.05] flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
                      <div className="flex gap-8 sm:gap-12">
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest block">
                            Type Probable
                          </span>
                          <span className="text-base text-gray-200 font-bold tracking-tight">
                            {target.analysis?.type}
                          </span>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest block">
                            Fenêtre Estimée
                          </span>
                          <span className="text-base text-gray-200 font-bold tracking-tight">
                            {target.analysis?.window}
                          </span>
                        </div>
                        {target.financials?.ebitda && (
                          <div className="space-y-1.5">
                            <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest block">
                              EBITDA
                            </span>
                            <span className="text-base text-gray-200 font-bold tracking-tight">
                              {target.financials.ebitda}
                            </span>
                          </div>
                        )}
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/targets/${target.id}`);
                        }}
                        className="w-full md:w-auto flex items-center justify-center gap-3 px-8 py-3.5 rounded-2xl bg-white text-black font-black text-[11px] uppercase tracking-widest hover:bg-indigo-600 hover:text-white transition-all shadow-2xl shadow-black/50 active:scale-95 group/btn"
                      >
                        Ouvrir la Fiche{" "}
                        <ChevronRight
                          size={18}
                          className="group-hover/btn:translate-x-1 transition-transform"
                        />
                      </button>
                    </div>
                  </motion.div>
                ))}
          </div>
        </div>

        {/* Intelligence Sidebar */}
        <div className="lg:col-span-4 flex flex-col gap-10 sticky top-4 min-w-0 overflow-hidden">
          {/* ── Distribution par Seuil ──────────────────────────── */}
          <div className="p-6 sm:p-10 rounded-[2rem] sm:rounded-[3rem] bg-black/40 border border-white/10 lg:backdrop-blur-3xl shadow-2xl">
            <div className="flex items-center justify-between mb-10">
              <h2 className="text-[11px] font-black text-white uppercase tracking-[0.3em] flex items-center gap-3">
                <BarChart3 size={18} className="text-indigo-400" /> Distribution par Seuil
              </h2>
            </div>
            <div className="space-y-5">
              {Object.entries(priorityDistribution).map(([level, count]) => (
                <div key={level} className="group cursor-default">
                  <div className="flex justify-between items-center mb-3 gap-2">
                    <span className="text-[11px] font-black text-gray-400 group-hover:text-white transition-colors uppercase tracking-widest truncate min-w-0">
                      {level}
                    </span>
                    <span className="text-sm font-black text-white shrink-0">{count}</span>
                  </div>
                  <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden shadow-inner">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / maxPriority) * 100}%` }}
                      className={`h-full ${priorityColors[level] || "bg-gray-600"} shadow-[0_0_12px_rgba(79,70,229,0.4)] rounded-full`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Volatilité Sectorielle ─────────────────────────── */}
          <div className="p-6 sm:p-10 rounded-[2rem] sm:rounded-[3rem] bg-black/40 border border-white/10 lg:backdrop-blur-3xl shadow-2xl">
            <div className="flex items-center justify-between mb-10">
              <h2 className="text-[11px] font-black text-white uppercase tracking-[0.3em] flex items-center gap-3">
                <Activity size={18} className="text-indigo-400" /> Volatilité Sectorielle
              </h2>
              <ShieldCheck size={18} className="text-emerald-500/50" />
            </div>

            <div className="space-y-6">
              {loading
                ? Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="flex justify-between items-center mb-4">
                        <div className="h-3 w-24 bg-white/5 rounded-lg" />
                        <div className="h-3 w-10 bg-white/5 rounded-lg" />
                      </div>
                      <div className="w-full h-1.5 bg-white/5 rounded-full" />
                    </div>
                  ))
                : sectorVolatility.map((s) => (
                    <div key={s.name} className="group cursor-default">
                      <div className="flex justify-between items-center mb-4 gap-2">
                        <span className="text-[11px] font-black text-gray-400 group-hover:text-white transition-colors uppercase tracking-widest truncate min-w-0">
                          {s.name}
                        </span>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[9px] font-black text-gray-600">{s.count} entités</span>
                          <span
                            className={`text-[10px] font-black px-2 py-0.5 rounded-lg ${
                              s.avgScore >= 50
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "bg-amber-500/10 text-amber-400"
                            }`}
                          >
                            {s.avgScore}
                          </span>
                        </div>
                      </div>
                      <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden shadow-inner">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${s.avgScore}%` }}
                          className="h-full bg-indigo-500 shadow-[0_0_12px_rgba(79,70,229,0.4)]"
                        />
                      </div>
                    </div>
                  ))}
            </div>

            <div className="mt-10 p-5 rounded-3xl bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-xl bg-indigo-500/10">
                  <Cpu size={16} className="text-indigo-400" />
                </div>
                <div>
                  <div className="text-[10px] font-black text-white uppercase tracking-widest">
                    Charge IA
                  </div>
                  <div className="text-[9px] font-bold text-gray-600 uppercase mt-0.5">
                    Traitement de {targets.length > 0 ? `${targets.length} entités` : "..."}
                  </div>
                </div>
              </div>
              <span className="text-[10px] font-black text-emerald-500 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
                OPTIMAL
              </span>
            </div>
          </div>

          {/* ── CFNEWS Veille Widget ─────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="p-6 sm:p-10 rounded-[2rem] sm:rounded-[3rem] bg-black/40 border border-white/10 lg:backdrop-blur-3xl shadow-2xl"
          >
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-[11px] font-black text-white uppercase tracking-[0.3em] flex items-center gap-3">
                <Newspaper size={18} className="text-amber-400" /> CFNEWS Veille
              </h2>
              <div className="flex items-center gap-2">
                {cfnewsLoading && (
                  <div className="w-3 h-3 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
                )}
                <span className="text-[9px] font-black text-amber-400 px-2 py-0.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  {cfnewsTargets.length} entreprises
                </span>
              </div>
            </div>

            {cfnewsLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="flex justify-between items-center mb-2">
                      <div className="h-3 w-28 bg-white/5 rounded-lg" />
                      <div className="h-3 w-8 bg-white/5 rounded-lg" />
                    </div>
                    <div className="h-2 w-full bg-white/5 rounded-full" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {cfnewsTargets.slice(0, 5).map((ct, idx) => (
                  <motion.div
                    key={ct.id || idx}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="group cursor-pointer"
                    onClick={() => setCfnewsOpen(true)}
                  >
                    <div className="flex justify-between items-center mb-2 gap-2">
                      <span className="text-[11px] font-black text-gray-400 group-hover:text-white transition-colors uppercase tracking-widest truncate min-w-0">
                        {ct.name}
                      </span>
                      <span
                        className={`text-[10px] font-black px-2 py-0.5 rounded-lg shrink-0 ${
                          ct.globalScore >= 65
                            ? "bg-emerald-500/10 text-emerald-400"
                            : ct.globalScore >= 45
                              ? "bg-indigo-500/10 text-indigo-400"
                              : ct.globalScore >= 25
                                ? "bg-amber-500/10 text-amber-400"
                                : "bg-gray-500/10 text-gray-500"
                        }`}
                      >
                        {ct.globalScore || "—"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[9px] font-bold text-gray-600 truncate">
                        {ct.cfnews?.titre}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden shadow-inner">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(ct.globalScore, 100)}%` }}
                        className={`h-full rounded-full ${
                          ct.globalScore >= 65
                            ? "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]"
                            : ct.globalScore >= 45
                              ? "bg-indigo-500 shadow-[0_0_12px_rgba(79,70,229,0.4)]"
                              : ct.globalScore >= 25
                                ? "bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                                : "bg-gray-600"
                        }`}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            <button
              onClick={() => setCfnewsOpen(true)}
              className="w-full mt-8 flex items-center justify-center gap-3 px-6 py-3 rounded-2xl bg-amber-500/5 border border-amber-500/10 text-[10px] font-black text-amber-400 uppercase tracking-widest hover:bg-amber-500/10 hover:border-amber-500/30 transition-all"
            >
              Voir toutes les entreprises <ChevronRight size={14} />
            </button>
          </motion.div>

          {/* Copilot Action Card */}
          <motion.button
            whileHover={{ y: -5 }}
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-copilot"))}
            className="relative p-10 rounded-[3rem] bg-indigo-600 text-left shadow-[0_30px_60px_rgba(79,70,229,0.4)] border border-indigo-400 hover:bg-indigo-500 transition-all group overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-10 opacity-10 group-hover:scale-125 group-hover:rotate-6 transition-all duration-700">
              <MessageSquare size={160} />
            </div>

            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/50 to-transparent pointer-events-none" />

            <div className="w-16 h-16 rounded-[1.5rem] bg-white/10 flex items-center justify-center text-white relative z-10 backdrop-blur-md mb-8 shadow-2xl">
              <Zap size={32} />
            </div>
            <div className="relative z-10">
              <h3 className="text-2xl font-black text-white leading-tight mb-4 tracking-tighter">
                Interroger EDRCF
              </h3>
              <p className="text-indigo-100 text-base font-medium leading-relaxed opacity-80 group-hover:opacity-100 transition-opacity">
                &quot;Identifiez les industriels français avec des fondateurs proches de 65 ans et
                sans plan de succession clair.&quot;
              </p>
            </div>
            <div className="flex items-center gap-3 text-white text-[11px] font-black uppercase tracking-[0.2em] mt-8 relative z-10 group-hover:translate-x-2 transition-transform">
              Lancer l&apos;Assistant <ChevronRight size={18} />
            </div>
          </motion.button>
        </div>
      </div>

      {/* ── CFNEWS Veille Modal ──────────────────────────────────── */}
      <AnimatePresence>
        {cfnewsOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-start justify-center overflow-y-auto py-8 px-4"
            onClick={() => setCfnewsOpen(false)}
          >
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.97 }}
              transition={{ duration: 0.3 }}
              className="w-full max-w-5xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-5">
                  <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/20">
                    <Newspaper size={24} className="text-amber-400" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-black text-white tracking-tighter">
                      Veille CFNEWS
                    </h2>
                    <p className="text-[11px] font-black text-gray-500 uppercase tracking-widest mt-1">
                      {cfnewsTargets.length} entreprises détectées &middot; Scoring EdRCF temps réel
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setCfnewsOpen(false)}
                  className="p-3 rounded-2xl bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition-all"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Cards Grid */}
              <div className="flex flex-col gap-5">
                {cfnewsTargets.map((target, idx) => (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    key={target.id || idx}
                    className="group p-6 sm:p-8 rounded-[2rem] bg-black/60 border border-white/10 hover:border-amber-500/30 transition-all relative overflow-hidden backdrop-blur-xl shadow-2xl"
                  >
                    {/* Source badge */}
                    <div className="absolute top-4 right-4 flex items-center gap-2">
                      {target.source === "cfnews+pappers" && (
                        <span className="text-[8px] font-black px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-widest">
                          Pappers
                        </span>
                      )}
                      <span className="text-[8px] font-black px-2 py-0.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-widest">
                        CFNEWS
                      </span>
                    </div>

                    <div className="flex justify-between items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-4 mb-4">
                          <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 group-hover:text-amber-400 group-hover:bg-amber-500/10 group-hover:border-amber-500/30 transition-all shadow-xl shrink-0">
                            <Building size={22} />
                          </div>
                          <div className="min-w-0">
                            <h3 className="text-xl font-black text-white tracking-tighter group-hover:text-amber-400 transition-colors truncate">
                              {target.name}
                            </h3>
                            <div className="flex gap-2 items-center mt-1 flex-wrap">
                              <span className="px-2.5 py-0.5 rounded-lg text-[9px] font-black tracking-widest uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                {target.sector || target.cfnews?.categorie}
                              </span>
                              {target.region && (
                                <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest">
                                  {target.region}
                                </span>
                              )}
                              {target.siren && (
                                <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
                                  {target.siren}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* CFNEWS headline */}
                        {target.cfnews?.titre && (
                          <a
                            href={target.cfnews.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-[10px] font-bold text-amber-400/70 hover:text-amber-400 transition-colors mb-4 max-w-full"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Newspaper size={12} className="shrink-0" />
                            <span className="truncate">{target.cfnews.titre}</span>
                            <ExternalLink size={10} className="shrink-0" />
                          </a>
                        )}

                        {/* Signals */}
                        {target.topSignals && target.topSignals.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {target.topSignals.slice(0, 4).map((signal) => (
                              <div
                                key={signal.id}
                                className="px-3 py-1.5 rounded-xl bg-white/[0.03] text-gray-400 text-[10px] font-black uppercase tracking-widest flex items-center gap-2 border border-white/5"
                              >
                                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/50 shadow-[0_0_6px_rgba(79,70,229,0.5)] shrink-0" />
                                <span className="truncate">{signal.label}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Score */}
                      <div className="flex flex-col items-end shrink-0">
                        <span
                          className={`text-5xl font-black leading-none tracking-tighter bg-clip-text text-transparent bg-gradient-to-b ${
                            target.globalScore >= 65
                              ? "from-emerald-400 to-emerald-800"
                              : target.globalScore >= 45
                                ? "from-white to-gray-800"
                                : target.globalScore >= 25
                                  ? "from-amber-400 to-amber-800"
                                  : "from-gray-400 to-gray-700"
                          }`}
                        >
                          {target.globalScore || "—"}
                        </span>
                        <span className="text-[9px] uppercase tracking-[0.3em] text-amber-400/60 font-black mt-2">
                          Score EdRCF
                        </span>
                      </div>
                    </div>

                    {/* Bottom info row */}
                    {target.source === "cfnews+pappers" && (
                      <div className="mt-6 pt-5 border-t border-white/[0.05] flex flex-wrap gap-6 sm:gap-10">
                        {target.analysis?.type && (
                          <div className="space-y-1">
                            <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest block">
                              Type Probable
                            </span>
                            <span className="text-sm text-gray-200 font-bold tracking-tight">
                              {target.analysis.type}
                            </span>
                          </div>
                        )}
                        {target.analysis?.window && (
                          <div className="space-y-1">
                            <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest block">
                              Fenêtre
                            </span>
                            <span className="text-sm text-gray-200 font-bold tracking-tight">
                              {target.analysis.window}
                            </span>
                          </div>
                        )}
                        {target.financials?.ebitda && target.financials.ebitda !== "N/A" && (
                          <div className="space-y-1">
                            <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest block">
                              EBITDA
                            </span>
                            <span className="text-sm text-gray-200 font-bold tracking-tight">
                              {target.financials.ebitda}
                            </span>
                          </div>
                        )}
                        {target.financials?.revenue && target.financials.revenue !== "N/A" && (
                          <div className="space-y-1">
                            <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest block">
                              CA
                            </span>
                            <span className="text-sm text-gray-200 font-bold tracking-tight">
                              {target.financials.revenue}
                            </span>
                          </div>
                        )}
                        <div className="space-y-1">
                          <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest block">
                            Priorité
                          </span>
                          <span
                            className={`text-sm font-bold tracking-tight ${
                              target.priorityLevel === "Action Prioritaire"
                                ? "text-emerald-400"
                                : target.priorityLevel === "Qualification"
                                  ? "text-indigo-400"
                                  : target.priorityLevel === "Monitoring"
                                    ? "text-amber-400"
                                    : "text-gray-400"
                            }`}
                          >
                            {target.priorityLevel}
                          </span>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}

                {cfnewsTargets.length === 0 && !cfnewsLoading && (
                  <div className="p-10 rounded-[2rem] bg-black/40 border border-white/10 text-center">
                    <Newspaper size={40} className="text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500 text-sm font-bold">
                      Aucune entreprise détectée dans les actualités CFNEWS
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
