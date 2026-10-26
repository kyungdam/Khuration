import { Tabs } from "expo-router";
import React from "react";

import { TabBar } from "../../components/TabBar";
import { colors } from "../../theme";

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <TabBar {...(props as unknown as React.ComponentProps<typeof TabBar>)} />}
      screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: colors.bg } }}
    >
      <Tabs.Screen name="index" />
      <Tabs.Screen name="notices" />
      <Tabs.Screen name="calendar" />
    </Tabs>
  );
}
