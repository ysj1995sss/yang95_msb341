import { isTopicGroupId } from "../data/triviaTopics";
import { createSetting } from "../utils/settings";

/** The trivia topic someone last chose, remembered between visits. */
export const topicSetting = createSetting<string>("closer.trivia.topic", "all", isTopicGroupId);
