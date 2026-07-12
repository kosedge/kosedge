"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import {
  getWallChartConferenceTeams,
  getWallChartOpponent,
  NFL_WALL_CHART_SEASON,
  NFL_WALL_CHART_WEEKS,
} from "@/lib/nfl-wall-chart-2026";
import "./nfl-wall-chart-2026.css";

function ConferenceBlock({ conference }: { conference: "AFC" | "NFC" }) {
  const teams = getWallChartConferenceTeams(conference);
  const railClass = conference === "AFC" ? "afc" : "nfc";

  return (
    <section className={`wall-chart-conference ${railClass}`} aria-label={`${conference} schedule`}>
      <div className={`wall-chart-conf-rail ${railClass}`}>
        <span>{conference}</span>
      </div>
      <div className="wall-chart-grid">
        <div className="wall-chart-row header">
          <div className="col-team">TEAM</div>
          {NFL_WALL_CHART_WEEKS.map((week) => (
            <div key={week}>WEEK {week}</div>
          ))}
          <div className="col-wins">WINS</div>
        </div>
        {teams.map((team) => (
          <div className="wall-chart-row" key={team.code}>
            <div className="wall-chart-team">
              <span className="team-name">{team.name}</span>
            </div>
            {NFL_WALL_CHART_WEEKS.map((week) => {
              const opponent = getWallChartOpponent(team.code, week);
              if (!opponent) {
                return (
                  <div className="wall-chart-cell bye" key={week}>
                    <span className="opp">BYE</span>
                  </div>
                );
              }
              const isAway = opponent.startsWith("@");
              return (
                <div
                  className={`wall-chart-cell ${isAway ? "away" : "home"}`}
                  key={week}
                >
                  <span className="opp">{opponent}</span>
                </div>
              );
            })}
            <div className="wall-chart-wins" aria-label={`${team.code} wins`} />
          </div>
        ))}
      </div>
    </section>
  );
}

function HelmetFootballArt() {
  return (
    <svg className="wall-chart-helmet-art" viewBox="0 0 160 100" aria-hidden>
      <defs>
        <linearGradient id="wcHelmet" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffe9a8" />
          <stop offset="40%" stopColor="#f5b942" />
          <stop offset="100%" stopColor="#a56a0a" />
        </linearGradient>
        <linearGradient id="wcBall" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8b4513" />
          <stop offset="50%" stopColor="#5c2e0a" />
          <stop offset="100%" stopColor="#3a1a05" />
        </linearGradient>
      </defs>
      {/* football */}
      <ellipse cx="118" cy="62" rx="28" ry="17" fill="url(#wcBall)" transform="rotate(-25 118 62)" />
      <path
        d="M102 54c10 5 24 5 34 0"
        fill="none"
        stroke="#f5e6d3"
        strokeWidth="1.6"
        transform="rotate(-25 118 62)"
      />
      <path d="M112 58h12M115 55v8M121 55v8" stroke="#f5e6d3" strokeWidth="1.2" />
      {/* helmet */}
      <path
        d="M18 58c2-28 24-46 52-42 18 2 34 16 38 34 2 10-2 18-12 22-8 4-18 4-28 2l-8 12c-2 2-6 2-8 0l-6-10c-12-2-24-8-28-18z"
        fill="url(#wcHelmet)"
      />
      <path
        d="M42 48c12-2 28 0 40 8 4 2 6 8 2 12-6 6-18 8-30 6-10-2-18-8-16-16 1-4 2-8 4-10z"
        fill="#1a1a1a"
        opacity="0.85"
      />
      <path d="M48 52h28" stroke="#f5b942" strokeWidth="2" strokeLinecap="round" />
      <path d="M70 38c10 4 18 14 20 26" fill="none" stroke="#ffe9a8" strokeWidth="2" opacity="0.5" />
    </svg>
  );
}

function EdgeGraph() {
  return (
    <svg className="wall-chart-edge-graph" viewBox="0 0 90 40" aria-hidden>
      <path
        d="M4 32 L18 24 L30 28 L46 12 L58 18 L74 6 L86 10"
        fill="none"
        stroke="#39ff14"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="86" cy="10" r="3.5" fill="#39ff14" />
    </svg>
  );
}

function NeonFooterArt() {
  return (
    <svg className="wall-chart-neon-art" viewBox="0 0 100 80" aria-hidden>
      <defs>
        <filter id="wcNeon">
          <feGaussianBlur stdDeviation="1.8" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <ellipse
        cx="38"
        cy="34"
        rx="26"
        ry="16"
        fill="none"
        stroke="#39ff14"
        strokeWidth="3"
        filter="url(#wcNeon)"
        transform="rotate(-30 38 34)"
      />
      <path
        d="M24 28c8 4 20 4 28 0"
        fill="none"
        stroke="#39ff14"
        strokeWidth="2"
        filter="url(#wcNeon)"
      />
      <path d="M28 38h18M32 34v10M40 34v10" stroke="#39ff14" strokeWidth="1.8" opacity="0.9" />
      <rect x="62" y="48" width="6" height="14" fill="#39ff14" opacity="0.45" />
      <rect x="71" y="40" width="6" height="22" fill="#39ff14" opacity="0.65" />
      <rect x="80" y="30" width="6" height="32" fill="#39ff14" opacity="0.85" />
      <rect x="89" y="20" width="6" height="42" fill="#39ff14" />
      <path d="M64 22 L96 8" stroke="#39ff14" strokeWidth="2.5" strokeLinecap="round" filter="url(#wcNeon)" />
      <path d="M90 4 L96 8 L91 12" fill="none" stroke="#39ff14" strokeWidth="2.5" />
    </svg>
  );
}

export function NflWallChart2026() {
  const scaleRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.45);

  useEffect(() => {
    const node = scaleRef.current;
    if (!node) return;

    const update = () => {
      setScale(Math.max(0.2, node.clientWidth / 2304));
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="wall-chart-page">
      <div className="wall-chart-toolbar print:hidden">
        <p>
          Printable {NFL_WALL_CHART_SEASON} NFL wall chart — sized for{" "}
          <strong>24×18″</strong> laminated paper. Cream cells are for wet-erase
          (home = green, away = blue). Print landscape, actual size, no margins.
        </p>
        <button type="button" onClick={() => window.print()}>
          Print 24×18
        </button>
      </div>

      <div className="wall-chart-stage">
        <div className="wall-chart-scale" ref={scaleRef}>
          <article
            className="wall-chart-sheet"
            style={{ transform: `scale(${scale})` }}
            aria-label={`${NFL_WALL_CHART_SEASON} NFL Wall Chart`}
          >
            <header className="wall-chart-header">
              <Image
                src="/brand/kosedge-logo-v2.png"
                alt="Kosedge Analytics"
                width={160}
                height={160}
                className="wall-chart-logo"
                priority
              />

              <div className="wall-chart-title-block">
                <p className="wall-chart-wordmark">KOSEDGE</p>
                <p className="wall-chart-analytics">★ ANALYTICS ★</p>
                <div className="wall-chart-ribbon">
                  <i className="notch left" aria-hidden />
                  <span>{NFL_WALL_CHART_SEASON} NFL WALL CHART</span>
                  <i className="notch right" aria-hidden />
                </div>
              </div>

              <div className="wall-chart-pitch">
                <div className="wall-chart-pitch-main">
                  <h2>THE KOS EDGE</h2>
                  <ul>
                    <li>MAKE SMARTER PLAYS.</li>
                    <li>TRACK THE SEASON.</li>
                    <li>CASH MORE TICKETS.</li>
                  </ul>
                  <EdgeGraph />
                </div>
                <HelmetFootballArt />
              </div>
            </header>

            <div className="wall-chart-rule" aria-hidden />

            <ConferenceBlock conference="AFC" />
            <ConferenceBlock conference="NFC" />

            <div className="wall-chart-rule" aria-hidden />

            <footer className="wall-chart-footer">
              <div className="wall-chart-survivor">
                <h3>SURVIVOR POOL</h3>
                <div className="wall-chart-survivor-weeks">
                  <span />
                  {NFL_WALL_CHART_WEEKS.map((week) => (
                    <span key={week}>{week}</span>
                  ))}
                </div>
                {[1, 2, 3].map((pool) => (
                  <div className="wall-chart-survivor-row" key={pool}>
                    <span>POOL {pool}</span>
                    {NFL_WALL_CHART_WEEKS.map((week) => (
                      <div
                        className="wall-chart-survivor-box"
                        key={week}
                        aria-label={`Pool ${pool} week ${week}`}
                      />
                    ))}
                  </div>
                ))}
              </div>

              <div className="wall-chart-tagline">
                <p>
                  DISCIPLINE.
                  <br />
                  DATA.
                  <br />
                  EDGE.
                  <br />
                  REPEAT.
                </p>
                <NeonFooterArt />
              </div>
            </footer>
          </article>
        </div>
      </div>
    </div>
  );
}
