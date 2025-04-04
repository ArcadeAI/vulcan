import { useStreamContext } from "@/providers/Stream";
import { HumanInterrupt } from "@langchain/langgraph/prebuilt";
import { useState } from "react";
import { StateView } from "./components/state-view";
import { ThreadActionsView } from "./components/thread-actions-view";

interface ThreadViewProps {
  interrupt: HumanInterrupt;
}

export function ThreadView({ interrupt }: ThreadViewProps) {
  const thread = useStreamContext();
  const [showDescription, setShowDescription] = useState(false);
  const [showState, setShowState] = useState(false);
  const showSidePanel = showDescription || showState;

  const handleShowSidePanel = (
    showState: boolean,
    showDescription: boolean,
  ) => {
    if (showState && showDescription) {
      console.error("Cannot show both state and description");
      return;
    }
    if (showState) {
      setShowDescription(false);
      setShowState(true);
    } else if (showDescription) {
      setShowState(false);
      setShowDescription(true);
    } else {
      setShowState(false);
      setShowDescription(false);
    }
  };

  return (
    <div className=" p-5 bg-gray-50/50 rounded-2xl overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {showSidePanel ? (
        <StateView
          handleShowSidePanel={handleShowSidePanel}
          description={interrupt.description}
          values={thread.values}
          view={showState ? "state" : "description"}
        />
      ) : (
        <ThreadActionsView
          interrupt={interrupt}
          handleShowSidePanel={handleShowSidePanel}
          showState={showState}
          showDescription={showDescription}
        />
      )}
    </div>
  );
}
