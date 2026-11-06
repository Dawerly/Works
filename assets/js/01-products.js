/* Вихідний масив даних, перенесений без змін. */

const PRODUCTS = [
  // === OCTOBAR ===
  { id: 1, cat: 'liquid', brand: 'Octobar', name: 'Octobar Ice Ice Baby', spec: "М'ята Кактус", price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/6854db2960b711f1852506dee8e103dd_4e9babf460bb11f1852506dee8e103dd-scaled.png' },

  { id: 3, cat: 'liquid', brand: 'Octobar', name: 'Octobar Go', spec: 'Зелене Яблуко', price: 184, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/040a06c85a8f11f1852506dee8e103dd_3dc37b8e5a8f11f1852506dee8e103dd.png' },
  { id: 4, cat: 'liquid', brand: 'Octobar', name: 'Octobar Go', spec: 'Кисла Вишня', price: 184, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/c7d8f9455a9211f1852506dee8e103dd_cff529e25a9211f1852506dee8e103dd.png' },
  { id: 5, cat: 'liquid', brand: 'Octobar', name: 'Octobar Go', spec: 'Кисла Слива', price: 184, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/1b5dc3255a9311f1852506dee8e103dd_23b381705a9311f1852506dee8e103dd.png' },
  { id: 6, cat: 'liquid', brand: 'Octobar', name: 'Octobar Go', spec: 'Персик Ананас', price: 184, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/d6294e7e5a9311f1852506dee8e103dd_dc46a8095a9311f1852506dee8e103dd.png' },

  { id: 7, cat: 'liquid', brand: 'Octobar', name: 'Octobar Fresh & Sour', spec: 'Зелене Яблуко', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/06/040a06c85a8f11f1852506dee8e103dd_3dc37b8e5a8f11f1852506dee8e103dd.png' },
  { id: 8, cat: 'liquid', brand: 'Octobar', name: 'Octobar Fresh & Sour', spec: "М'ята Базилік", price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/c6ac373ad1de11f0852506dee8e103dd_3207dd27749b11f1852506dee8e103dd.png' },
  { id: 9, cat: 'liquid', brand: 'Octobar', name: 'Octobar Fresh & Sour', spec: 'Орбіт', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/1e4517e2f93f11ef84f606c525bef229_7f3140b6749c11f1852506dee8e103dd.png' },

  { id: 10, cat: 'liquid', brand: 'Octobar', name: 'Octobar X', spec: 'Ягідний Мікс', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/07/b75ddc2cf93e11ef84f606c525bef229_aeb4fde9754711f1852506dee8e103dd.png' },
  { id: 11, cat: 'liquid', brand: 'Octobar', name: 'Octobar X', spec: 'Чорниця Ментол', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/b75ddc31f93e11ef84f606c525bef229_b805f0c4754711f1852506dee8e103dd.png' },
  { id: 12, cat: 'liquid', brand: 'Octobar', name: 'Octobar X', spec: 'Вишневий Сік', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/b75ddc30f93e11ef84f606c525bef229_d23856e5754711f1852506dee8e103dd.png' },
  { id: 13, cat: 'liquid', brand: 'Octobar', name: 'Octobar X', spec: "Лимон М'ята", price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/b75ddc28f93e11ef84f606c525bef229_fd713230754711f1852506dee8e103dd.png' },

  { id: 14, cat: 'liquid', brand: 'Octobar', name: 'Octobar Prime', spec: "Яблучно-М'ятна Цукерка", price: 234, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/bd47b43ed20811f0852506dee8e103dd_7b99c29674d911f1852506dee8e103dd.png' },
  { id: 15, cat: 'liquid', brand: 'Octobar', name: 'Octobar Prime', spec: 'Абрикос Лайм', price: 234, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/92836e73f93e11ef84f606c525bef229_90f532ed74d911f1852506dee8e103dd.png' },
  { id: 16, cat: 'liquid', brand: 'Octobar', name: 'Octobar Prime', spec: 'Виноград Лід', price: 234, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/98a80b38f93e11ef84f606c525bef229_1c80d4b974d911f1852506dee8e103dd.png' },

  { id: 17, cat: 'liquid', brand: 'Octobar', name: 'Octobar NFT', spec: 'Ягідний Чай', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/437213bbf93e11ef84f606c525bef229_37cd772a74d511f1852506dee8e103dd.png' },
  { id: 18, cat: 'liquid', brand: 'Octobar', name: 'Octobar NFT', spec: 'Енергетик', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/437213bef93e11ef84f606c525bef229_5a95f83a74d511f1852506dee8e103dd.png' },
  { id: 19, cat: 'liquid', brand: 'Octobar', name: 'Octobar NFT', spec: 'Виноград Чорниця Лід', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/1ea3434df93e11ef84f606c525bef229_b38f82f074d111f1852506dee8e103dd.png' },
  { id: 20, cat: 'liquid', brand: 'Octobar', name: 'Octobar NFT', spec: 'Кисле Яблуко', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/37187396f93e11ef84f606c525bef229_14dd22fb74d211f1852506dee8e103dd.png' },

  { id: 21, cat: 'liquid', brand: 'Octobar', name: 'Octobar Strong', spec: 'Ожиновий Крамбл', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/127bed6df93e11ef84f606c525bef229_bc87b37574dd11f1852506dee8e103dd.png' },
  { id: 22, cat: 'liquid', brand: 'Octobar', name: 'Octobar Strong', spec: 'Кавун', price: 204, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/1893f483f93e11ef84f606c525bef229_484d99cb74de11f1852506dee8e103dd.png' },

  // === BLACK LIMIT & TWINS ===
  { id: 23, cat: 'liquid', brand: 'Black Limit', name: 'Black Limit', spec: 'Вишня Лід', price: 174, image: 'https://dymok.net.ua/images/stories/virtuemart/product/cherry_ice_blacksalt.jpg' },
  { id: 24, cat: 'liquid', brand: 'Black Limit', name: 'Black Limit', spec: "Кучерява М'ята", price: 174, image: 'https://dymok.net.ua/images/stories/virtuemart/product/spearmint_blacksalt.jpg' },
  { id: 25, cat: 'liquid', brand: 'Black Limit', name: 'Black Limit', spec: 'Полуниця Лід', price: 174, image: 'https://dymok.net.ua/images/stories/virtuemart/product/stawberry_ice_blacksalt.jpg' },

  { id: 26, cat: 'liquid', brand: 'Twins', name: 'Twins', spec: 'Жувальна Гумка', price: 174, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/e7d90ee1f93d11ef84f606c525bef229_41b1023c754a11f1852506dee8e103dd.png' },
  { id: 27, cat: 'liquid', brand: 'Twins', name: 'Twins', spec: 'Ментол', price: 174, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/b190c36feadd11f0852506dee8e103dd_e5198dbf754a11f1852506dee8e103dd.png' },
  { id: 28, cat: 'liquid', brand: 'Twins', name: 'Twins', spec: 'Лісові Ягоди', price: 174, image: 'https://octolab.com.ua/wp-content/uploads/2026/04/e7d90ee9f93d11ef84f606c525bef229_00cf26f0754b11f1852506dee8e103dd.png' },

  // === CHASER ===
  { id: 29, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: "Прохолодна м'ята", price: 214, image: 'https://mychase.com.ua/content/images/10/310x310l85nn0/nabir-chaser-beat-arctic-house-30-ml-30-mh-88494133843842.webp' },
  { id: 30, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Смородина Малина', price: 214, image: 'https://mychase.com.ua/content/images/1/310x310l85nn0/nabir-chaser-beat-bass-berry-30-ml-30-mh-83357052656754.webp' },
  { id: 31, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Чорничне Морозиво', price: 214, image: 'https://mychase.com.ua/content/images/42/310x310l85nn0/nabir-chaser-beat-blue-ice-beat-30-ml-30-mh-30319824470349.webp' },
  { id: 32, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Чорнична Жуйка', price: 214, image: 'https://mychase.com.ua/content/images/45/310x310l85nn0/nabir-chaser-beat-bubble-berry-tune-30-ml-30-mh-31420939340929.webp' },
  { id: 33, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Вишнева Кола', price: 214, image: 'https://mychase.com.ua/content/images/7/310x310l85nn0/nabir-chaser-beat-cherry-pulse-30-ml-30-mh-92930804248141.webp' },
  { id: 34, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Виноград Вишня', price: 214, image: 'https://mychase.com.ua/content/images/13/310x310l85nn0/nabir-chaser-beat-grape-cherry-30-ml-30-mh-43992119997778.webp' },
  { id: 35, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Виноград Енергетик', price: 214, image: 'https://mychase.com.ua/content/images/4/310x310l85nn0/nabir-chaser-beat-grape-techno-30-ml-30-mh-85262290325137.webp' },
  { id: 36, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Ківі Маракуя Гуава', price: 214, image: 'https://mychase.com.ua/content/images/44/310x310l85nn0/nabir-chaser-beat-hawaii-wibe-30-ml-30-mh-55692937737635.webp' },
  { id: 37, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Персик Лід', price: 214, image: 'https://mychase.com.ua/content/images/41/310x310l85nn0/nabir-chaser-beat-icy-peach-flow-30-ml-30-mh-20633455306119.webp' },
  { id: 38, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Соковитий Ананас', price: 214, image: 'https://mychase.com.ua/content/images/48/310x310l85nn0/nabir-chaser-beat-pineapple-bass-30-ml-30-mh-77282950388981.webp' },
  { id: 39, cat: 'liquid', brand: 'Chaser', name: 'Chaser Beat', spec: 'Кавун', price: 214, image: 'https://mychase.com.ua/content/images/38/310x310l85nn0/nabir-chaser-beat-watermelon-wave-30-ml-30-mh-52882384636740.webp' },

  { id: 40, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Рожевий Лимонад', price: 214, image: 'https://mychase.com.ua/content/images/42/310x248l85nn0/32399962811818.webp' },
  { id: 41, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Балі', price: 214, image: 'https://mychase.com.ua/content/images/10/310x248l85nn0/24641002744781.webp' },
  { id: 42, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Ожина Кисла Малина', price: 214, image: 'https://mychase.com.ua/content/images/48/310x248l85nn0/48541780120170.webp' },
  { id: 43, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Енергетик Виноград', price: 214, image: 'https://mychase.com.ua/content/images/27/310x248l85nn0/72304758449044.webp' },
  { id: 44, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Ківі Суниця', price: 214, image: 'https://mychase.com.ua/content/images/33/310x248l85nn0/92212312546041.webp' },
  { id: 45, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: "Лимон М'ята", price: 214, image: 'https://mychase.com.ua/content/images/45/310x248l85nn0/51028008881451.webp' },
  { id: 46, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Потрійне Кисле Яблуко', price: 214, image: 'https://mychase.com.ua/content/images/16/310x248l85nn0/13460010431448.webp' },
  { id: 47, cat: 'liquid', brand: 'Chaser', name: 'Chaser Black', spec: 'Жуйка', price: 214, image: 'https://mychase.com.ua/content/images/4/310x248l85nn0/46298027118867.webp' },

  { id: 48, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Ягідний лимонад', price: 264, image: 'https://mychase.com.ua/content/images/31/310x310l85nn0/nabir-chaser-lux-berry-lemonade-30-ml-30-mh-62844411238906.webp' },
  { id: 49, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Смородина персик лимон', price: 264, image: 'https://mychase.com.ua/content/images/23/310x310l85nn0/nabir-chaser-lux-blackcurrant-lemon-peach-30-ml-30-mh-79702628650041.webp' },
  { id: 50, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: "Чорниця м'ята", price: 264, image: 'https://mychase.com.ua/content/images/7/310x248l85nn0/13284477282719.webp' },
  { id: 51, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Кокос диня', price: 264, image: 'https://mychase.com.ua/content/images/1/310x248l85nn0/65158652864909.webp' },
  { id: 52, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Кисле яблуко', price: 264, image: 'https://mychase.com.ua/content/images/34/310x310l85nn0/nabir-chaser-lux-sour-apple-30-ml-30-mh-97114396831463.webp' },
  { id: 53, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Енергетик', price: 264, image: 'https://mychase.com.ua/content/images/4/310x248l85nn0/17996928215482.webp' },
  { id: 54, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: "Виноград М'ята", price: 264, image: 'https://mychase.com.ua/content/images/23/310x248l85nn0/56705729953943.webp' },
  { id: 55, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Персиковий Чай', price: 264, image: 'https://mychase.com.ua/content/images/25/310x310l85nn0/nabir-chaser-lux-tea-peach-30-ml-30-mh-76353264920026.webp' },
  { id: 56, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: "Турбо М'ята", price: 264, image: 'https://mychase.com.ua/content/images/13/310x248l85nn0/54817033170869.webp' },
  { id: 57, cat: 'liquid', brand: 'Chaser', name: 'Chaser Lux', spec: 'Вітамін', price: 264, image: 'https://mychase.com.ua/content/images/10/310x248l85nn0/67444754947294.webp' },

  { id: 58, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: "Базилик М'ята", price: 214, image: 'https://mychase.com.ua/content/images/38/310x310l85nn0/komponenty-chaser-mix-bazylik-miata-44908799936386.webp' },
  { id: 59, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: 'Енергетик Вишня', price: 214, image: 'https://mychase.com.ua/content/images/19/310x310l85nn0/komponenty-chaser-mix-enerhetyk-vyshnia-30-ml-30-mh-42738870649934.webp' },
  { id: 60, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: 'Блакитна Малина Лимонад', price: 214, image: 'https://mychase.com.ua/content/images/32/310x310l85nn0/komponenty-chaser-mix-blakytna-malyna-lymonad-37523837824060.webp' },
  { id: 61, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: 'Гуава Персик', price: 214, image: 'https://mychase.com.ua/content/images/43/310x310l85nn0/ridyna-mix-for-pods-huava-sokovytyi-persyk-30-ml-30-mh-95975203349634.webp' },
  { id: 62, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: 'Орбіт', price: 214, image: 'https://mychase.com.ua/content/images/26/310x310l85nn0/komponenty-chaser-mix-miatnyi-orbit-30-ml-63949078629760.webp' },
  { id: 63, cat: 'liquid', brand: 'Chaser', name: 'Chaser Mix Ultra', spec: 'Полуниця Банан', price: 214, image: 'https://mychase.com.ua/content/images/29/310x310l85nn0/komponenty-chaser-mix-polunytsia-solodkyi-banan-89164018898793.webp' },

  { id: 64, cat: 'liquid', brand: 'Chaser', name: 'Chaser My Mint', spec: "Журавлина м'ята", price: 214, image: 'https://mychase.com.ua/content/images/13/310x310l85nn0/nabir-chaser-my-mint-cranberry-mint-30-ml-30-mh-45259239864986.webp' },
  { id: 65, cat: 'liquid', brand: 'Chaser', name: 'Chaser My Mint', spec: 'Мятний льодяник', price: 214, image: 'https://mychase.com.ua/content/images/7/310x310l85nn0/nabir-chaser-my-mint-sweet-mint-30-ml-30-mh-67888168812520.webp' },
  { id: 66, cat: 'liquid', brand: 'Chaser', name: 'Chaser My Mint', spec: 'Мятна жуйка', price: 214, image: 'https://mychase.com.ua/content/images/42/310x310l85nn0/nabir-chaser-my-mint-cool-mint-30-ml-30-mh-58482311692331.webp' },

  { id: 67, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Апельсин', price: 214, image: 'https://mychase.com.ua/content/images/37/310x310l85nn0/nabir-chaser-for-pods-apelsyn-30-ml-30-mh-22992486165815.webp' },
  { id: 68, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Блакитна Малина', price: 214, image: 'https://mychase.com.ua/content/images/23/310x310l85nn0/ridyna-salt-for-pods-smak-blakytna-malyna-30ml-30-mh-35398841262937.webp' },
  { id: 69, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Виноград', price: 214, image: 'https://mychase.com.ua/content/images/14/310x310l85nn0/ridyna-salt-for-pods-smak-chornyi-solodkyi-vynohrad-30-ml-30-mh-23173492815580.webp' },
  { id: 70, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Вишня Ментол', price: 214, image: 'https://mychase.com.ua/content/images/31/310x310l85nn0/nabir-komponentiv-salt-for-pods-smak-vyshnia-mentol-30-ml-30-mh-87368503869891.webp' },
  { id: 71, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: "М'ята", price: 214, image: 'https://mychase.com.ua/content/images/10/310x310l85nn0/nabir-komponentiv-salt-for-pods-stiikyi-klasychnyi-smak-miaty-30-ml-30-mh-96769217409789.webp' },
  { id: 72, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Смородина Ментол', price: 214, image: 'https://mychase.com.ua/content/images/24/310x310l85nn0/nabir-komponentiv-mix-smak-smorodyny-ta-aromat-mentolu-30-ml-30-mh-58557038776000.webp' },
  { id: 73, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Чорниця Ментол', price: 214, image: 'https://mychase.com.ua/content/images/2/310x310l85nn0/nabir-komponentiv-mix-smak-chornytsia-i-kholodnyi-mentol-30-ml-30-mh-56613646770858.webp' },
  { id: 74, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Вишня', price: 214, image: 'https://mychase.com.ua/content/images/19/310x310l85nn0/ridyna-salt-for-pods-smak-zrila-vyshnia-30-ml-30-mh-38073533681826.webp' },
  { id: 75, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Кавун', price: 214, image: 'https://mychase.com.ua/content/images/26/310x310l85nn0/23907506820388.webp' },
  { id: 76, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Кавун ментол', price: 214, image: 'https://mychase.com.ua/content/images/20/310x310l85nn0/nabir-komponentiv-salt-for-pods-smak-kavun-mentol-10-ml-30-mh-33545738533194.webp' },
  { id: 77, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Абрикос', price: 214, image: 'https://mychase.com.ua/content/images/33/310x310l85nn0/nabir-chaser-for-pods-abrykos-30-ml-30-mh-91654208658896.webp' },
  { id: 78, cat: 'liquid', brand: 'Chaser', name: 'Chaser Pods 30ml', spec: 'Драгонфрут', price: 214, image: 'https://mychase.com.ua/content/images/15/310x310l85nn0/nabir-chaser-for-pods-zhovtyi-drahonfrut-30-ml-30-mh-51285845655165.webp' },

  // === NOVA & FLIP & ELFIQ & LUCKY ===
  { id: 79, cat: 'liquid', brand: 'NOVA', name: 'NOVA', spec: 'Блакитна Малина Енергетик', price: 214, image: 'https://dartvaper.ua/files/products/bluerazz-energy_1.800x800.jpg.webp' },
  { id: 80, cat: 'liquid', brand: 'NOVA', name: 'NOVA', spec: 'Подвійний Виноград', price: 214, image: 'https://dartvaper.ua/files/products/double-grape.800x800.jpg.webp' },
  { id: 81, cat: 'liquid', brand: 'NOVA', name: 'NOVA', spec: 'Кавун Диня', price: 214, image: 'https://dartvaper.ua/files/products/watermelon-melon.800x800.jpg.webp' },

  { id: 82, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: 'Кола', price: 170, image: 'https://dymok.net.ua/images/stories/virtuemart/product/resized/flip_salt_cola25.jpg' },
  { id: 83, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: 'Ківі холодок', price: 170, image: 'https://dymok.net.ua/images/stories/virtuemart/product/resized/flip_salt_coldkiwi25.jpg' },
  { id: 84, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: "Подвійна м'ята", price: 170, image: 'https://dymok.net.ua/images/stories/virtuemart/product/resized/flip_salt_doublemint25.jpg' },
  { id: 85, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: 'Червоний виноград', price: 170, image: 'https://dartvaper.ua/files/products/nabor-flip-red-grape-30-ml_1.800x800.jpg.webp' },
  { id: 86, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: 'Диня', price: 170, image: 'https://dartvaper.ua/files/products/nabor-flip-melon-30-ml.800x800.jpg.webp' },
  { id: 87, cat: 'liquid', brand: 'Flip', name: 'Набор Flip 30ml 50mg', spec: "М'ята", price: 170, image: 'https://dartvaper.ua/files/products/nabor-flip-mint-30-ml.600x600.jpg.webp' },

  { id: 88, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: 'Льодяник', price: 255, image: 'https://dartvaper.ua/files/products/nabor-elfliq-elf-jack-30-ml.600x600.jpg.webp' },
  { id: 89, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: "М'ята", price: 255, image: 'https://dartvaper.ua/files/products/miata.600x600.jpg.webp' },
  { id: 90, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: 'Груша Смородина Лимон', price: 255, image: 'https://dartvaper.ua/files/products/kekueue.600x600.jpg.webp' },
  { id: 91, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: 'Вишня Лимон Персик', price: 255, image: 'https://dartvaper.ua/files/products/kekeroprog86789.600x600.jpg.webp' },
  { id: 92, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: 'Вишня', price: 255, image: 'https://dartvaper.ua/files/products/chirik.600x600.jpg.webp' },
  { id: 93, cat: 'liquid', brand: 'ELFIQ', name: 'ELFIQ 12ml', spec: 'Чорниця Лимон', price: 255, image: 'https://dartvaper.ua/files/products/ayaya.600x600.jpg.webp' },

  { id: 94, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: "Лісові ягоди, м'ята", price: 225, image: 'https://dartvaper.ua/files/products/87uhloiz.600x600.jpg.webp' },
  { id: 95, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Зелене яблуко, лічі', price: 225, image: 'https://dartvaper.ua/files/products/89iuht66.600x600.jpg.webp' },
  { id: 96, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Зелений чай', price: 225, image: 'https://dartvaper.ua/files/products/kmnuiokr.600x600.jpg.webp' },
  { id: 97, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Желейні ведмедики', price: 225, image: 'https://dartvaper.ua/files/products/hugyt.600x600.jpg.webp' },
  { id: 98, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Гранат, вишня', price: 225, image: 'https://dartvaper.ua/files/products/iiiese.600x600.jpg.webp' },
  { id: 99, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Малина', price: 225, image: 'https://dartvaper.ua/files/products/nhgt6ygvcde4.600x600.jpg.webp' },
  { id: 100, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Літній чай', price: 225, image: 'https://dartvaper.ua/files/products/2026-04-27-19.005.28.600x600.jpg.webp' },
  { id: 101, cat: 'liquid', brand: 'LUCKY', name: 'LUCKY Chrome 15ml', spec: 'Тропік', price: 225, image: 'https://dartvaper.ua/files/products/yayayafyai.800x800.jpg.webp' },

  // === HOOKAH ===
  { id: 102, cat: 'access', brand: 'PIXTEA', name: 'Заправка до кальяну PIXTEA', spec: 'ALIENS CANDY', price: 120, image: 'https://cdn.kalyan-city.com.ua/products/images/pixtea-aliens-candy-100g.png?width=520' },
  { id: 103, cat: 'access', brand: 'PIXTEA', name: 'Заправка до кальяну PIXTEA', spec: 'GRAPE VS MELON', price: 120, image: 'https://aladin-kyiv.com/images/products/chayna-sumish-pixtea-grape-vs-melon-vynohrad-vs-dynya-100-hr.webp' },
  { id: 104, cat: 'access', brand: 'PIXTEA', name: 'Заправка до кальяну PIXTEA', spec: 'VIVID FUSION', price: 120, image: 'https://cdn.kalyan-city.com.ua/products/images/pixtea-vivid-fusion-100g.png?width=520' },
  
  // === DEVICES (ПОД-СИСТЕМИ) ===
  { id: 105, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Brown', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Brown' },
  { id: 106, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Jelly Blue', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Blue' },
  { id: 107, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Jelly Green', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Green' },
  { id: 108, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Jelly Orange', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Orange' },
  { id: 109, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Jelly Pink', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Pink' },
  { id: 110, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Plume Blue', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+P.Blue' },
  { id: 111, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Plume White', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+White' },
  { id: 112, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Titanium Black', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Black' },
  { id: 113, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Plume Pink', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+P.Pink' },
  { id: 114, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6 Mini', spec: 'Titanium Silver', price: 900, image: 'https://placehold.co/400x400/334155/fff?text=XROS+6+Mini:+Silver' },

  { id: 115, cat: 'pod', brand: 'OXVA', name: 'OXVA XLIM Go Lite', spec: 'Стандарт', price: 450, image: 'https://placehold.co/400x400/334155/fff?text=XLIM+Go+Lite' },
  
  { id: 116, cat: 'pod', brand: 'Smok', name: 'Smok novo 6', spec: 'Purple', price: 1200, image: 'https://placehold.co/400x400/334155/fff?text=Smok+Novo+6:+Purple' },
  { id: 117, cat: 'pod', brand: 'Smok', name: 'Smok novo 6', spec: 'Red', price: 1200, image: 'https://placehold.co/400x400/334155/fff?text=Smok+Novo+6:+Red' },

  { id: 118, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Pearl White', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+White' },
  { id: 119, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Silk Brown', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Brown' },
  { id: 120, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Carbon Fiber Gray', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Carbon' },
  { id: 121, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Silk Green', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Green' },
  { id: 122, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Silk Gray', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Gray' },
  { id: 123, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Cosmic Black', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Black' },
  { id: 124, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Aurora Blue', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Blue' },
  { id: 125, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Slate Black', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Slate' },
  { id: 126, cat: 'pod', brand: 'Vaporesso', name: 'VAPORESSO XROS 6', spec: 'Dreamy Pink', price: 1250, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+6:+Pink' },

  { id: 127, cat: 'pod', brand: 'OXVA', name: 'OXVA XLIM GO', spec: 'Кольори в асортименті', price: 650, image: 'https://placehold.co/400x400/0f172a/fff?text=XLIM+GO' },
  { id: 128, cat: 'pod', brand: 'OXVA', name: 'OXVA XLIM GO 2', spec: 'Green Ripple', price: 650, image: 'https://placehold.co/400x400/0f172a/fff?text=XLIM+GO+2' },
  { id: 129, cat: 'pod', brand: 'OXVA', name: 'OXVA XLIM PRO 2', spec: 'Кольори в асортименті', price: 1100, image: 'https://placehold.co/400x400/0f172a/fff?text=XLIM+PRO+2' },
  { id: 130, cat: 'pod', brand: 'Vaporesso', name: 'XROS 5 NANO', spec: 'Кольори в асортименті', price: 1200, image: 'https://placehold.co/400x400/1e293b/fff?text=XROS+5+NANO' },

  // === CARTRIDGES / ПОДИ ===
  { id: 131, cat: 'access', brand: 'OXVA', name: 'Картридж Oxva top fill 2ml', spec: '0.4 / 0.6 / 0.8 ом', price: 150, image: 'https://placehold.co/400x400/475569/fff?text=Oxva+Cartridge' },
  { id: 132, cat: 'access', brand: 'Voopoo', name: 'Картридж Voopoo vmate v2', spec: '0.4 / 1.2 ом', price: 140, image: 'https://placehold.co/400x400/475569/fff?text=Voopoo+Cartridge' },
  { id: 133, cat: 'access', brand: 'Vaporesso', name: 'Картридж Xros 2ml', spec: '0.8 ом', price: 140, image: 'https://placehold.co/400x400/475569/fff?text=XROS+2ml+Cartridge' },
  { id: 134, cat: 'access', brand: 'Vaporesso', name: 'Картридж Xros 3ml', spec: '0.4 / 0.8 ом', price: 150, image: 'https://placehold.co/400x400/475569/fff?text=XROS+3ml+Cartridge' },
  { id: 135, cat: 'access', brand: 'Lost Vape', name: 'Картридж Ursa nano', spec: '0.6 / 0.8 ом', price: 140, image: 'https://placehold.co/400x400/475569/fff?text=Ursa+Cartridge' },

  // === АКСЕСУАРИ ТА БУСТЕРИ ===
  { id: 136, cat: 'access', brand: 'Інше', name: 'Гліцерин', spec: 'Основа (10/30ml)', price: 10, image: 'https://placehold.co/400x400/64748b/fff?text=Glycerin' },
  { id: 137, cat: 'access', brand: 'Steampuff', name: 'Бустер Steampuff', spec: 'Підсилювач', price: 126, image: 'https://placehold.co/400x400/64748b/fff?text=Steampuff+Booster' },
  { id: 138, cat: 'access', brand: 'Chaser', name: 'Підсилювач міцності Chaser', spec: 'Бустер', price: 135, image: 'https://placehold.co/400x400/64748b/fff?text=Chaser+Booster' },
  { id: 139, cat: 'access', brand: 'Octolab', name: 'Брелок-відкривачка Octolab', spec: 'Original', price: 150, image: 'https://placehold.co/400x400/64748b/fff?text=Octolab+Opener' },
  { id: 140, cat: 'access', brand: 'Інше', name: 'ICE SHOT', spec: 'Холодок', price: 30, image: 'https://placehold.co/400x400/64748b/fff?text=ICE+SHOT' },
  { id: 141, cat: 'access', brand: 'Інше', name: 'SOUR SHOT', spec: 'Кислинка', price: 30, image: 'https://placehold.co/400x400/64748b/fff?text=SOUR+SHOT' },

  // === 30 ПОПУЛЯРНИХ ПОД-СИСТЕМ (Vandale / Популярні хіти) ===

  // === 20 ПОПУЛЯРНИХ ОДНОРАЗОК (Вандал / Популярні хіти) ===
  { id: 142, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar 1500', spec: 'Blue Razz Lemonade', price: 319, image: 'https://placehold.co/400x400/db2777/fff?text=ElfBar+1500:+BlueRazz' },
  { id: 143, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar 1500', spec: 'Watermelon', price: 319, image: 'https://placehold.co/400x400/db2777/fff?text=ElfBar+1500:+Watermelon' },
  { id: 144, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar Lux 1500', spec: 'Strawberry Banana', price: 299, image: 'https://placehold.co/400x400/db2777/fff?text=Lux+1500:+Str.Banana' },
  { id: 145, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar BC4000', spec: 'Cranberry Grape', price: 469, image: 'https://placehold.co/400x400/db2777/fff?text=BC4000:+Cran.Grape' },
  { id: 146, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar BC4000', spec: 'Triple Berry Ice', price: 469, image: 'https://placehold.co/400x400/db2777/fff?text=BC4000:+TripleBerry' },
  { id: 147, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar TE5000', spec: 'Juicy Peach', price: 669, image: 'https://placehold.co/400x400/db2777/fff?text=TE5000:+Peach' },
  { id: 148, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar TE5000', spec: 'Apple Peach', price: 669, image: 'https://placehold.co/400x400/db2777/fff?text=TE5000:+ApplePeach' },
  { id: 149, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar TE6000', spec: 'Strawberry Ice', price: 799, image: 'https://placehold.co/400x400/db2777/fff?text=TE6000:+Strawberry' },
  { id: 150, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar PI7000', spec: 'Blackberry Cranberry', price: 889, image: 'https://placehold.co/400x400/db2777/fff?text=PI7000:+Blackberry' },
  { id: 151, cat: 'disposable', brand: 'Elf Bar', name: 'Elf Bar ELFA Pod Kit', spec: 'Pear', price: 399, image: 'https://placehold.co/400x400/db2777/fff?text=ELFA:+Pear' },

  { id: 152, cat: 'disposable', brand: 'Joyetech', name: 'Joyetech VAAL 1500', spec: 'Tobacco', price: 269, image: 'https://placehold.co/400x400/4f46e5/fff?text=VAAL+1500:+Tobacco' },
  { id: 153, cat: 'disposable', brand: 'Joyetech', name: 'Joyetech VAAL 1500', spec: 'Aloe Grape', price: 269, image: 'https://placehold.co/400x400/4f46e5/fff?text=VAAL+1500:+AloeGrape' },
  { id: 154, cat: 'disposable', brand: 'Joyetech', name: 'Joyetech VAAL 2500M', spec: 'Cotton Candy', price: 349, image: 'https://placehold.co/400x400/4f46e5/fff?text=VAAL+2500M:+Cotton' },

  { id: 155, cat: 'disposable', brand: 'Waka', name: 'Waka SoPro PA600', spec: 'Cherry Ice', price: 450, image: 'https://placehold.co/400x400/ea580c/fff?text=Waka+PA600:+Cherry' },
  { id: 156, cat: 'disposable', brand: 'Waka', name: 'Waka SoPro DM8000i', spec: 'Watermelon Chill', price: 750, image: 'https://placehold.co/400x400/ea580c/fff?text=Waka+DM8000i:+Melon' },

  { id: 157, cat: 'disposable', brand: 'Lost Mary', name: 'Lost Mary BM600', spec: 'Triple Melon', price: 350, image: 'https://placehold.co/400x400/16a34a/fff?text=LostMary+BM600:+Melon' },
  { id: 158, cat: 'disposable', brand: 'Lost Mary', name: 'Lost Mary BM5000', spec: 'Blueberry Raspberry Lemon', price: 699, image: 'https://placehold.co/400x400/16a34a/fff?text=BM5000:+Blueberry' },
  { id: 159, cat: 'disposable', brand: 'Lost Mary', name: 'Lost Mary MO5000', spec: 'Grape Ice', price: 699, image: 'https://placehold.co/400x400/16a34a/fff?text=MO5000:+GrapeIce' },

  { id: 160, cat: 'disposable', brand: 'HQD', name: 'HQD Cuvie Plus', spec: 'Ice Mint', price: 380, image: 'https://placehold.co/400x400/0284c7/fff?text=HQD+Plus:+Mint' },
  { id: 161, cat: 'disposable', brand: 'Airis', name: 'Airis Lux P5000', spec: 'Strawberry Mango', price: 519, image: 'https://placehold.co/400x400/9333ea/fff?text=Airis+P5000:+Mango' },
];
