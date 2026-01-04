"use client"

import { TopNav } from "@/components/layout/TopNav"
import { PhaseStepper } from "@/components/layout/PhaseStepper"
import { Phase1Upload } from "@/components/phases/Phase1Upload"
import { Phase2Process } from "@/components/phases/Phase2Process"
import { Phase3Rank } from "@/components/phases/Phase3Rank"
import { Phase4Results } from "@/components/phases/Phase4Results"
import { useAppContext } from "@/contexts/AppContext"

export default function Home() {
  const { currentCollection } = useAppContext()
  const phase = currentCollection.phase

  return (
    <div className="min-h-screen bg-gray-50">
      <TopNav />
      <PhaseStepper />

      <main className="min-h-screen bg-gray-50">
        {phase === 1 && <Phase1Upload />}
        {phase === 2 && <Phase2Process />}
        {phase === 3 && <Phase3Rank />}
        {phase === 4 && <Phase4Results />}
      </main>
    </div>
  )
}
