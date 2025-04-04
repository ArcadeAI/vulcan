import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { HumanInterrupt } from "@langchain/langgraph/prebuilt";
import { toast } from "sonner";
import { StringParam, useQueryParam } from "use-query-params";
import useInterruptedActions from "../hooks/use-interrupted-actions";
import { constructOpenInStudioURL } from "../utils";
import { InboxItemInput } from "./inbox-item-input";
import { ThreadIdCopyable } from "./thread-id";

interface ThreadActionsViewProps {
  interrupt: HumanInterrupt;
  handleShowSidePanel: (showState: boolean, showDescription: boolean) => void;
  showState: boolean;
  showDescription: boolean;
}

function ButtonGroup({
  handleShowState,
  handleShowDescription,
  showingState,
  showingDescription,
}: {
  handleShowState: () => void;
  handleShowDescription: () => void;
  showingState: boolean;
  showingDescription: boolean;
}) {
  return (
    <div className="flex flex-row gap-0 items-center justify-center">
      <Button
        variant="outline"
        className={cn(
          "rounded-l-md rounded-r-none border-r-[0px]",
          showingState ? "text-black" : "bg-white",
        )}
        size="sm"
        onClick={handleShowState}
      >
        State
      </Button>
      <Button
        variant="outline"
        className={cn(
          "rounded-l-none rounded-r-md border-l-[0px]",
          showingDescription ? "text-black" : "bg-white",
        )}
        size="sm"
        onClick={handleShowDescription}
      >
        Description
      </Button>
    </div>
  );
}

export function ThreadActionsView({
  interrupt,
  handleShowSidePanel,
  showDescription,
  showState,
}: ThreadActionsViewProps) {
  const [threadId] = useQueryParam("threadId", StringParam);
  const {
    acceptAllowed,
    hasEdited,
    hasAddedResponse,
    streaming,
    supportsMultipleMethods,
    streamFinished,
    loading,
    handleSubmit,
    handleIgnore,
    handleResolve,
    setSelectedSubmitType,
    setHasAddedResponse,
    setHasEdited,
    humanResponse,
    setHumanResponse,
    initialHumanInterruptEditValue,
  } = useInterruptedActions({
    interrupt,
  });
  const [apiUrl] = useQueryParam("apiUrl", StringParam);

  const handleOpenInStudio = () => {
    if (!apiUrl) {
      toast.error("Error", {
        description: "Please set the LangGraph deployment URL in settings.",
        duration: 5000,
        richColors: true,
        closeButton: true,
      });
      return;
    }

    const studioUrl = constructOpenInStudioURL(apiUrl, threadId ?? undefined);
    window.open(studioUrl, "_blank");
  };

  const threadTitle = interrupt.action_request.action || "Unknown";
  const actionsDisabled = loading || streaming;

  return (
    <div className="flex flex-wrap min-h-full gap-9 ">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between w-full gap-3 overflow-hidden">
        <div className="flex items-center justify-start gap-3 overflow-hidden text-ellipsis">
          <p className="text-2xl tracking-tighter text-pretty truncate">
            {threadTitle}
          </p>
          {threadId && <ThreadIdCopyable threadId={threadId} />}
        </div>
        <div className="flex flex-row gap-2 items-center justify-start">
          {apiUrl && (
            <Button
              size="sm"
              variant="outline"
              className="flex items-center gap-1 bg-white"
              onClick={handleOpenInStudio}
            >
              Studio
            </Button>
          )}
          <ButtonGroup
            handleShowState={() => handleShowSidePanel(true, false)}
            handleShowDescription={() => handleShowSidePanel(false, true)}
            showingState={showState}
            showingDescription={showDescription}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="overflow-auto">
        <InboxItemInput
          acceptAllowed={acceptAllowed}
          hasEdited={hasEdited}
          hasAddedResponse={hasAddedResponse}
          interruptValue={interrupt}
          humanResponse={humanResponse}
          initialValues={initialHumanInterruptEditValue.current}
          setHumanResponse={setHumanResponse}
          streaming={streaming}
          streamFinished={streamFinished}
          supportsMultipleMethods={supportsMultipleMethods}
          setSelectedSubmitType={setSelectedSubmitType}
          setHasAddedResponse={setHasAddedResponse}
          setHasEdited={setHasEdited}
          handleSubmit={handleSubmit}
        />
      </div>
    </div>
  );
}
