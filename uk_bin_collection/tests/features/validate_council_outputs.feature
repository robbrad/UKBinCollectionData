Feature: Test each council output matches expected results

    Scenario Outline: Validate Council Output
        Given the council: <council>
        When we scrape the data from <council>
        Then the result is valid json
        And the output should validate against the schema

		@AdurAndWorthingCouncils
		Examples: AdurAndWorthingCouncils
		| council |
		| AdurAndWorthingCouncils |

		@ArunCouncil
		Examples: ArunCouncil
		| council |
		| ArunCouncil |

        @AylesburyValeCouncil
		Examples: AylesburyValeCouncil
		| council |
		| AylesburyValeCouncil |

        @BarnetCouncil
		Examples: BarnetCouncil
		| council |
		| BarnetCouncil |

        @BarnsleyMBCouncil
		Examples: BarnsleyMBCouncil
		| council |
		| BarnsleyMBCouncil |

        @BasingstokeCouncil
		Examples: BasingstokeCouncil
		| council |
		| BasingstokeCouncil |

        @BathAndNorthEastSomersetCouncil
		Examples: BathAndNorthEastSomersetCouncil
		| council |
		| BathAndNorthEastSomersetCouncil |

        @BCPCouncil
		Examples: BCPCouncil
		| council |
		| BCPCouncil |

		@BedfordBoroughCouncil
		Examples: BedfordBoroughCouncil
		| council |
		| BedfordBoroughCouncil |

        @BedfordshireCouncil
		Examples: BedfordshireCouncil
		| council |
		| BedfordshireCouncil |

        @BexleyCouncil
		Examples: BexleyCouncil
		| council |
		| BexleyCouncil |

        @BirminghamCityCouncil
		Examples: BirminghamCityCouncil
		| council |
		| BirminghamCityCouncil |

        @BlackburnCouncil
		Examples: BlackburnCouncil
		| council |
		| BlackburnCouncil |

        @BoltonCouncil
		Examples: BoltonCouncil
		| council |
		| BoltonCouncil |

        @BracknellForestCouncil
		Examples: BracknellForestCouncil
		| council |
		| BracknellForestCouncil |

        @BradfordMDC
		Examples: BradfordMDC
		| council |
		| BradfordMDC |

        @BrightonandHoveCityCouncil
		Examples: BrightonandHoveCityCouncil
		| council |
		| BrightonandHoveCityCouncil |

        @BristolCityCouncil
		Examples: BristolCityCouncil
		| council |
		| BristolCityCouncil |

        @BromleyBoroughCouncil
		Examples: BromleyBoroughCouncil
		| council |
		| BromleyBoroughCouncil |

        @BroxtoweBoroughCouncil
		Examples: BroxtoweBoroughCouncil
		| council |
		| BroxtoweBoroughCouncil |

        @BuckinghamshireCouncil
		Examples: BuckinghamshireCouncil
		| council |
		| BuckinghamshireCouncil |

        @BuryCouncil
		Examples: BuryCouncil
		| council |
		| BuryCouncil |

        @CalderdaleCouncil
		Examples: CalderdaleCouncil
		| council |
		| CalderdaleCouncil |

        @CannockChaseDistrictCouncil
		Examples: CannockChaseDistrictCouncil
		| council |
		| CannockChaseDistrictCouncil |

        @CardiffCouncil
		Examples: CardiffCouncil
		| council |
		| CardiffCouncil |

        @CastlepointDistrictCouncil
		Examples: CastlepointDistrictCouncil
		| council |
		| CastlepointDistrictCouncil |

        @CharnwoodBoroughCouncil
		Examples: CharnwoodBoroughCouncil
		| council |
		| CharnwoodBoroughCouncil |

        @ChelmsfordCityCouncil
		Examples: ChelmsfordCityCouncil
		| council |
		| ChelmsfordCityCouncil |

        @CheshireEastCouncil
		Examples: CheshireEastCouncil
		| council |
		| CheshireEastCouncil |

		@CheshireWestAndChesterCouncil
		Examples: CheshireWestAndChesterCouncil
		| council |
		| CheshireWestAndChesterCouncil |

        @ChorleyCouncil
		Examples: ChorleyCouncil
		| council |
		| ChorleyCouncil |

        @ConwyCountyBorough
		Examples: ConwyCountyBorough
		| council |
		| ConwyCountyBorough |

        @CrawleyBoroughCouncil
		Examples: CrawleyBoroughCouncil
		| council |
		| CrawleyBoroughCouncil |

        @CroydonCouncil
		Examples: CroydonCouncil
		| council |
		| CroydonCouncil |

        @DerbyshireDalesDistrictCouncil
		Examples: DerbyshireDalesDistrictCouncil
		| council |
		| DerbyshireDalesDistrictCouncil |

        @DoncasterCouncil
		Examples: DoncasterCouncil
		| council |
		| DoncasterCouncil |

        @DorsetCouncil
		Examples: DorsetCouncil
		| council |
		| DorsetCouncil |

        @DoverDistrictCouncil
		Examples: DoverDistrictCouncil
		| council |
		| DoverDistrictCouncil |

        @DurhamCouncil
		Examples: DurhamCouncil
		| council |
		| DurhamCouncil |

        @EastCambridgeshireCouncil
		Examples: EastCambridgeshireCouncil
		| council |
		| EastCambridgeshireCouncil |

        @EastDevonDC
		Examples: EastDevonDC
		| council |
		| EastDevonDC |

        @EastleighBoroughCouncil
		Examples: EastleighBoroughCouncil
		| council |
		| EastleighBoroughCouncil |

        @EastLindseyDistrictCouncil
		Examples: EastLindseyDistrictCouncil
		| council |
		| EastLindseyDistrictCouncil |

        @EastRidingCouncil
		Examples: EastRidingCouncil
		| council |
		| EastRidingCouncil |

        @EastSuffolkCouncil
		Examples: EastSuffolkCouncil
		| council |
		| EastSuffolkCouncil |

        @EnvironmentFirst
		Examples: EnvironmentFirst
		| council |
		| EnvironmentFirst |

		@EppingForestDistrictCouncil
		Examples: EppingForestDistrictCouncil
		| council |
		| EppingForestDistrictCouncil |

        @ErewashBoroughCouncil
		Examples: ErewashBoroughCouncil
		| council |
		| ErewashBoroughCouncil |

        @FarehamBoroughCouncil
		Examples: FarehamBoroughCouncil
		| council |
		| FarehamBoroughCouncil |

        @FenlandDistrictCouncil
		Examples: FenlandDistrictCouncil
		| council |
		| FenlandDistrictCouncil |

        @ForestOfDeanDistrictCouncil
		Examples: ForestOfDeanDistrictCouncil
		| council |
		| ForestOfDeanDistrictCouncil |

        @GatesheadCouncil
		Examples: GatesheadCouncil
		| council |
		| GatesheadCouncil |

        @GedlingBoroughCouncil
		Examples: GedlingBoroughCouncil
		| council |
		| GedlingBoroughCouncil |

        @GlasgowCityCouncil
		Examples: GlasgowCityCouncil
		| council |
		| GlasgowCityCouncil |

        @GuildfordCouncil
		Examples: GuildfordCouncil
		| council |
		| GuildfordCouncil |

        @HaltonBoroughCouncil
		Examples: HaltonBoroughCouncil
		| council |
		| HaltonBoroughCouncil |

        @HaringeyCouncil
		Examples: HaringeyCouncil
		| council |
		| HaringeyCouncil |

        @HarrogateBoroughCouncil
		Examples: HarrogateBoroughCouncil
		| council |
		| HarrogateBoroughCouncil |

        @HighPeakCouncil
		Examples: HighPeakCouncil
		| council |
		| HighPeakCouncil |

		@HounslowCouncil
		Examples: HounslowCouncil
		| council |
		| HounslowCouncil |

		@HullCityCouncil
		Examples: HullCityCouncil
		| council |
		| HullCityCouncil |

        @HuntingdonDistrictCouncil
		Examples: HuntingdonDistrictCouncil
		| council |
		| HuntingdonDistrictCouncil |

        @KingstonUponThamesCouncil
		Examples: KingstonUponThamesCouncil
		| council |
		| KingstonUponThamesCouncil |

		@KirkleesCouncil
		Examples: KirkleesCouncil
		| council |
		| KirkleesCouncil |

		@KnowsleyMBCouncil
		Examples: KnowsleyMBCouncil
		| council |
		| KnowsleyMBCouncil |

        @LancasterCityCouncil
		Examples: LancasterCityCouncil
		| council |
		| LancasterCityCouncil |

        @LeedsCityCouncil
		Examples: LeedsCityCouncil
		| council |
		| LeedsCityCouncil |

        @LisburnCastlereaghCityCouncil
		Examples: LisburnCastlereaghCityCouncil
		| council |
		| LisburnCastlereaghCityCouncil |

        @LiverpoolCityCouncil
		Examples: LiverpoolCityCouncil
		| council |
		| LiverpoolCityCouncil |

        @LondonBoroughHounslow
		Examples: LondonBoroughHounslow
		| council |
		| LondonBoroughHounslow |

        @LondonBoroughRedbridge
		Examples: LondonBoroughRedbridge
		| council |
		| LondonBoroughRedbridge |

        @MaldonDistrictCouncil
		Examples: MaldonDistrictCouncil
		| council |
		| MaldonDistrictCouncil |

        @MalvernHillsDC
		Examples: MalvernHillsDC
		| council |
		| MalvernHillsDC |

        @ManchesterCityCouncil
		Examples: ManchesterCityCouncil
		| council |
		| ManchesterCityCouncil |

		@MansfieldDistrictCouncil
		Examples: MansfieldDistrictCouncil
		| council |
		| MansfieldDistrictCouncil |

        @MertonCouncil
		Examples: MertonCouncil
		| council |
		| MertonCouncil |

        @MidAndEastAntrimBoroughCouncil
		Examples: MidAndEastAntrimBoroughCouncil
		| council |
		| MidAndEastAntrimBoroughCouncil |

        @MidSussexDistrictCouncil
		Examples: MidSussexDistrictCouncil
		| council |
		| MidSussexDistrictCouncil |

        @MiltonKeynesCityCouncil
		Examples: MiltonKeynesCityCouncil
		| council |
		| MiltonKeynesCityCouncil |

        @MoleValleyDistrictCouncil
        Examples: MoleValleyDistrictCouncil
        | council |
        | MoleValleyDistrictCouncil |

        @NeathPortTalbotCouncil
		Examples: NeathPortTalbotCouncil
		| council |
		| NeathPortTalbotCouncil |

        @NewarkAndSherwoodDC
		Examples: NewarkAndSherwoodDC
		| council |
		| NewarkAndSherwoodDC |

        @NewcastleCityCouncil
		Examples: NewcastleCityCouncil
		| council |
		| NewcastleCityCouncil |

        @NewhamCouncil
		Examples: NewhamCouncil
		| council |
		| NewhamCouncil |

        @NewportCityCouncil
		Examples: NewportCityCouncil
		| council |
		| NewportCityCouncil |

        @NorthEastDerbyshireDistrictCouncil
		Examples: NorthEastDerbyshireDistrictCouncil
		| council |
		| NorthEastDerbyshireDistrictCouncil |

        @NorthEastLincs
		Examples: NorthEastLincs
		| council |
		| NorthEastLincs |

        @NorthKestevenDistrictCouncil
		Examples: NorthKestevenDistrictCouncil
		| council |
		| NorthKestevenDistrictCouncil |

        @NorthLanarkshireCouncil
		Examples: NorthLanarkshireCouncil
		| council |
		| NorthLanarkshireCouncil |

        @NorthLincolnshireCouncil
		Examples: NorthLincolnshireCouncil
		| council |
		| NorthLincolnshireCouncil |

        @NorthNorfolkDistrictCouncil
		Examples: NorthNorfolkDistrictCouncil
		| council |
		| NorthNorfolkDistrictCouncil |

        @NorthNorthamptonshireCouncil
		Examples: NorthNorthamptonshireCouncil
		| council |
		| NorthNorthamptonshireCouncil |

        @NorthSomersetCouncil
		Examples: NorthSomersetCouncil
		| council |
		| NorthSomersetCouncil |

        @NorthTynesideCouncil
		Examples: NorthTynesideCouncil
		| council |
		| NorthTynesideCouncil |

        @NorthumberlandCouncil
		Examples: NorthumberlandCouncil
		| council |
		| NorthumberlandCouncil |

        @NorthWestLeicestershire
		Examples: NorthWestLeicestershire
		| council |
		| NorthWestLeicestershire |

		@NorthYorkshire
		Examples: NorthYorkshire
		| council |
		| NorthYorkshire |

        @NottinghamCityCouncil
		Examples: NottinghamCityCouncil
		| council |
		| NottinghamCityCouncil |

        @OldhamCouncil
		Examples: OldhamCouncil
		| council |
		| OldhamCouncil |

        @PortsmouthCityCouncil
		Examples: PortsmouthCityCouncil
		| council |
		| PortsmouthCityCouncil |

        @PrestonCityCouncil
		Examples: PrestonCityCouncil
		| council |
		| PrestonCityCouncil |

        @ReadingBoroughCouncil
		Examples: ReadingBoroughCouncil
		| council |
		| ReadingBoroughCouncil |

        @ReigateAndBansteadBoroughCouncil
		Examples: ReigateAndBansteadBoroughCouncil
		| council |
		| ReigateAndBansteadBoroughCouncil |

        @RenfrewshireCouncil
		Examples: RenfrewshireCouncil
		| council |
		| RenfrewshireCouncil |

        @RhonddaCynonTaffCouncil
		Examples: RhonddaCynonTaffCouncil
		| council |
		| RhonddaCynonTaffCouncil |

        @RochdaleCouncil
		Examples: RochdaleCouncil
		| council |
		| RochdaleCouncil |

		@RochfordCouncil
		Examples: RochfordCouncil
		| council |
		| RochfordCouncil |

        @RugbyBoroughCouncil
		Examples: RugbyBoroughCouncil
		| council |
		| RugbyBoroughCouncil |

        @RushcliffeBoroughCouncil
		Examples: RushcliffeBoroughCouncil
		| council |
		| RushcliffeBoroughCouncil |

        @RushmoorCouncil
		Examples: RushmoorCouncil
		| council |
		| RushmoorCouncil |

        @SalfordCityCouncil
		Examples: SalfordCityCouncil
		| council |
		| SalfordCityCouncil |

        @SevenoaksDistrictCouncil
		Examples: SevenoaksDistrictCouncil
		| council |
		| SevenoaksDistrictCouncil |

        @SheffieldCityCouncil
		Examples: SheffieldCityCouncil
		| council |
		| SheffieldCityCouncil |

        @ShropshireCouncil
		Examples: ShropshireCouncil
		| council |
		| ShropshireCouncil |

		@SolihullCouncil
		Examples: SolihullCouncil
		| council |
		| SolihullCouncil |

        @SomersetCouncil
		Examples: SomersetCouncil
		| council |
		| SomersetCouncil |

        @SouthAyrshireCouncil
		Examples: SouthAyrshireCouncil
		| council |
		| SouthAyrshireCouncil |

        @SouthCambridgeshireCouncil
		Examples: SouthCambridgeshireCouncil
		| council |
		| SouthCambridgeshireCouncil |

        @SouthGloucestershireCouncil
		Examples: SouthGloucestershireCouncil
		| council |
		| SouthGloucestershireCouncil |

        @SouthLanarkshireCouncil
		Examples: SouthLanarkshireCouncil
		| council |
		| SouthLanarkshireCouncil |

        @SouthNorfolkCouncil
		Examples: SouthNorfolkCouncil
		| council |
		| SouthNorfolkCouncil |

        @SouthOxfordshireCouncil
		Examples: SouthOxfordshireCouncil
		| council |
		| SouthOxfordshireCouncil |

        @SouthTynesideCouncil
		Examples: SouthTynesideCouncil
		| council |
		| SouthTynesideCouncil |

        @StAlbansCityAndDistrictCouncil
        Examples: StAlbansCityAndDistrictCouncil
        | council |
        | StAlbansCityAndDistrictCouncil |

        @StaffordshireMoorlandsDistrictCouncil
		Examples: StaffordshireMoorlandsDistrictCouncil
		| council |
		| StaffordshireMoorlandsDistrictCouncil |

        @StHelensBC
		Examples: StHelensBC
		| council |
		| StHelensBC |

        @StockportBoroughCouncil
		Examples: StockportBoroughCouncil
		| council |
		| StockportBoroughCouncil |

        @StokeOnTrentCityCouncil
		Examples: StokeOnTrentCityCouncil
		| council |
		| StokeOnTrentCityCouncil |

        @StratfordUponAvonCouncil
		Examples: StratfordUponAvonCouncil
		| council |
		| StratfordUponAvonCouncil |

		@StroudDistrictCouncil
		Examples: StroudDistrictCouncil
		| council |
		| StroudDistrictCouncil |

		@SunderlandCityCouncil
		Examples: SunderlandCityCouncil
		| council |
		| SunderlandCityCouncil |

        @SwaleBoroughCouncil
		Examples: SwaleBoroughCouncil
		| council |
		| SwaleBoroughCouncil |

        @TamesideMBCouncil
		Examples: TamesideMBCouncil
		| council |
		| TamesideMBCouncil |

		@TandridgeDistrictCouncil
		Examples: TandridgeDistrictCouncil
		| council |
		| TandridgeDistrictCouncil |

		@TelfordAndWrekinCouncil
		Examples: TelfordAndWrekinCouncil
		| council |
		| TelfordAndWrekinCouncil |

		@TendringDistrictCouncil
		Examples: TendringDistrictCouncil
		| council |
		| TendringDistrictCouncil |

        @TestValleyBoroughCouncil
		Examples: TestValleyBoroughCouncil
		| council |
		| TestValleyBoroughCouncil |

        @TonbridgeAndMallingBC
		Examples: TonbridgeAndMallingBC
		| council |
		| TonbridgeAndMallingBC |

        @TorbayCouncil
		Examples: TorbayCouncil
		| council |
		| TorbayCouncil |

        @TorridgeDistrictCouncil
		Examples: TorridgeDistrictCouncil
		| council |
		| TorridgeDistrictCouncil |

        @ValeofGlamorganCouncil
		Examples: ValeofGlamorganCouncil
		| council |
		| ValeofGlamorganCouncil |

        @ValeofWhiteHorseCouncil
		Examples: ValeofWhiteHorseCouncil
		| council |
		| ValeofWhiteHorseCouncil |

        @WakefieldCityCouncil
		Examples: WakefieldCityCouncil
		| council |
		| WakefieldCityCouncil |

		@WalthamForest
		Examples: WalthamForest
		| council |
		| WalthamForest |

        @WarwickDistrictCouncil
		Examples: WarwickDistrictCouncil
		| council |
		| WarwickDistrictCouncil |

        @WaverleyBoroughCouncil
		Examples: WaverleyBoroughCouncil
		| council |
		| WaverleyBoroughCouncil |

        @WealdenDistrictCouncil
		Examples: WealdenDistrictCouncil
		| council |
		| WealdenDistrictCouncil |

        @WelhatCouncil
		Examples: WelhatCouncil
		| council |
		| WelhatCouncil |

		@WestBerkshireCouncil
		Examples: WestBerkshireCouncil
		| council |
		| WestBerkshireCouncil |

        @WestLindseyDistrictCouncil
		Examples: WestLindseyDistrictCouncil
		| council |
		| WestLindseyDistrictCouncil |

        @WestLothianCouncil
		Examples: WestLothianCouncil
		| council |
		| WestLothianCouncil |

		@WestNorthamptonshireCouncil
		Examples: WestNorthamptonshireCouncil
		| council |
		| WestNorthamptonshireCouncil |

        @WestSuffolkCouncil
		Examples: WestSuffolkCouncil
		| council |
		| WestSuffolkCouncil |

        @WiganBoroughCouncil
		Examples: WiganBoroughCouncil
		| council |
		| WiganBoroughCouncil |

        @WiltshireCouncil
		Examples: WiltshireCouncil
		| council |
		| WiltshireCouncil |

        @WindsorAndMaidenheadCouncil
		Examples: WindsorAndMaidenheadCouncil
		| council |
		| WindsorAndMaidenheadCouncil |

        @WokingBoroughCouncil
		Examples: WokingBoroughCouncil
		| council |
		| WokingBoroughCouncil |

		@WyreCouncil
		Examples: WyreCouncil
		| council |
		| WyreCouncil |

        @YorkCouncil
		Examples: YorkCouncil
		| council |
		| YorkCouncil |
