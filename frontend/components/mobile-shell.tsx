"use client";

import { useState } from "react";

import type { AppBootstrap, TabKey } from "@/lib/contracts";
import { NAV_ITEMS } from "@/lib/contracts";
import { TabIcon, StatusBar } from "@/components/ui-shell";
import {
  CareScreen,
  CoachScreen,
  InsightsScreen,
  MeScreen,
  RecordsScreen,
  TodayScreen,
} from "@/components/tab-screens";
import { cn } from "@/lib/display";

export function MobileShell({ bootstrap }: { bootstrap: AppBootstrap }) {
  const [activeTab, setActiveTab] = useState<TabKey>("today");
  const firstName = bootstrap.profile.name.split(" ")[0] ?? bootstrap.profile.name;

  return (
    <section className="w-full sm:max-w-[420px]">
      <div className="mx-auto h-dvh w-full overflow-hidden bg-shell sm:h-[844px] sm:max-w-[390px] sm:rounded-[40px] sm:border sm:border-white/70 sm:shadow-phone">
        <div className="relative flex h-full flex-col">
          <StatusBar />

          <div className="shell-scrollbar flex-1 overflow-y-auto px-5 pb-28 pt-14">
            {activeTab === "today" && (
              <TodayScreen bootstrap={bootstrap} firstName={firstName} />
            )}
            {activeTab === "coach" && <CoachScreen />}
            {activeTab === "records" && <RecordsScreen bootstrap={bootstrap} />}
            {activeTab === "insights" && <InsightsScreen bootstrap={bootstrap} />}
            {activeTab === "care" && <CareScreen bootstrap={bootstrap} />}
            {activeTab === "me" && <MeScreen bootstrap={bootstrap} />}
          </div>

          <nav className="absolute inset-x-0 bottom-0 flex items-stretch border-t border-border/80 bg-white/95 px-2 pt-2 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur">
            {NAV_ITEMS.map((item) => {
              const active = item.key === activeTab;

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setActiveTab(item.key)}
                  className="flex flex-1 flex-col items-center justify-center gap-1 rounded-2xl px-1 py-2 text-[11px] font-medium text-muted transition-transform duration-150 ease-out active:scale-95"
                >
                  <span
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-2xl transition-colors",
                      active ? "bg-accent-soft text-accent" : "text-muted",
                    )}
                  >
                    <TabIcon tab={item.key} active={active} />
                  </span>
                  <span className={active ? "text-accent" : "text-muted"}>
                    {item.label}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </section>
  );
}
