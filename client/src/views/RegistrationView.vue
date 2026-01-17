<template>
  <div
    class="w-full flex lg:flex-row flex-col items-center lg:items-start bg-primary"
  >
    <div
      class="xl:w-1/4 lg:w-2/6 lg:h-screen flex flex-col items-center relative top-0"
    >
      <div class="w-60 mt-10 flex flex-col">
        <div class="logo w-full h-12 flex justify-center lg:justify-start">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            height="42px"
            width="auto"
            class="mr-1"
          >
            <path
              d="M2 8.99374C2 5.68349 4.67654 3 8.00066 3H15.9993C19.3134 3 22 5.69478 22 8.99374V21H8.00066C4.68659 21 2 18.3052 2 15.0063V8.99374ZM14 11V13H16V11H14ZM8 11V13H10V11H8Z"
            ></path>
          </svg>
          <span class="text-4xl font-bold">Bridge</span>
        </div>
        <div class="text-sm text-center lg:text-start">
          The shotrest bridge for connection
        </div>
      </div>
      <div class="mt-auto lg:block hidden">
        <img class="auth-img relative" src="@/assets/auth-img.png" alt="" />
      </div>
    </div>
    <div
      class="xl:w-3/4 lg:w-4/6 w-11/12 h-auto lg:mr-10 my-10 py-6 sm:px-10 px-2 flex flex-col items-center justify-center rounded-2xl bg-color-background-mute"
    >
      <RouterView />
    </div>
  </div>
</template>
