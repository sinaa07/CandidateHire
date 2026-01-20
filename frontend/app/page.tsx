"use client"

import { TopNav } from "@/components/layout/TopNav"
import { PhaseStepper } from "@/components/layout/PhaseStepper"
import { Phase1Upload } from "@/components/phases/Phase1Upload"
import { Phase2Process } from "@/components/phases/Phase2Process"
import { Phase3Rank } from "@/components/phases/Phase3Rank"
import { Phase4Results } from "@/components/phases/Phase4Results"
import { RAGChat } from "@/components/features/RAGChat"
import { useAppContext } from "@/contexts/AppContext"

export default function Home() {
  const { currentCollection } = useAppContext()
  const phase = currentCollection.phase
  const showChat = phase === 4 && currentCollection.collection_id

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex flex-col">
      <TopNav />
      <PhaseStepper />

      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 overflow-y-auto bg-[#F5F5F5]">
          {phase === 1 && <Phase1Upload />}
          {phase === 2 && <Phase2Process />}
          {phase === 3 && <Phase3Rank />}
          {phase === 4 && <Phase4Results />}
        </main>
        {showChat && <RAGChat />}
      </div>
    </div>
  )
}
