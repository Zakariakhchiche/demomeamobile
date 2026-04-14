import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface PipelineCard {
  id: string;
  name: string;
  sector: string;
  ebitda: string;
  priority: string;
  score: number;
  window?: string;
  region?: string;
  tags?: string[];
}

interface PipelineStage {
  id: string;
  title: string;
  color: string;
  cards: PipelineCard[];
}

interface PipelineData {
  data: PipelineStage[];
}

export function usePipeline() {
  return useQuery<PipelineData>({
    queryKey: ["pipeline"],
    queryFn: async () => {
      const res = await fetch("/api/pipeline");
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useMoveCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ cardId, fromStage, toStage, newIndex }: { cardId: string; fromStage: string; toStage: string; newIndex: number }) => {
      const res = await fetch("/api/pipeline/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId, from_stage: fromStage, to_stage: toStage, new_index: newIndex }),
      });
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    // Optimistic update: move the card immediately in the UI
    onMutate: async ({ cardId, fromStage, toStage, newIndex }) => {
      await queryClient.cancelQueries({ queryKey: ["pipeline"] });
      const previous = queryClient.getQueryData<PipelineData>(["pipeline"]);

      queryClient.setQueryData<PipelineData>(["pipeline"], (old) => {
        if (!old) return old;
        const stages = old.data.map((s) => ({ ...s, cards: [...s.cards] }));
        const srcStage = stages.find((s) => s.id === fromStage);
        const dstStage = stages.find((s) => s.id === toStage);
        if (!srcStage || !dstStage) return old;

        const cardIndex = srcStage.cards.findIndex((c) => c.id === cardId);
        if (cardIndex === -1) return old;
        const [card] = srcStage.cards.splice(cardIndex, 1);
        dstStage.cards.splice(newIndex, 0, card);

        return { data: stages };
      });

      return { previous };
    },
    // Rollback on error
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["pipeline"], context.previous);
      }
    },
    // Always refetch after mutation settles
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}
