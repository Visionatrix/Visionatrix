<script setup lang="ts"></script>

<template>
	<main class="grid lg:grid-cols-2 place-items-center pt-16 pb-8 md:pt-8">
    <div class="p-24 md:order-1 hidden md:block">
      <img
        class="rounded-full transition-transform transform hover:scale-125"
        src="~/assets/img/example.png"
        alt="Starship starts the engine"
        loading="eager"
        format="avif"
        width="512"
        height="512"
      />
    </div>

    <div>
      <h1 class="text-5xl lg:text-6xl xl:text-7xl font-bold lg:tracking-tight">
        Production ready AI workflows
      </h1>
      <p class="text-lg mt-4 text-slate-600 max-w-xl">
        AI Media Wizard proposes a set of automated ComfyUI flows for different types of image or video generation tasks.
        <wbr /> You can quickly setup available workflows and ask your prompts.
      </p>
      <div class="mt-6 flex flex-col sm:flex-row gap-3">
        <UButton :to="'/workflows'">Check out workflows</UButton>
      </div>
    </div>
  </main>
</template>
